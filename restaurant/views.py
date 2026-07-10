import json
import logging
from decimal import Decimal
from django.db import transaction
from django.contrib import messages
from django.template.loader import render_to_string
from django.http import JsonResponse, HttpResponse
from django.shortcuts import redirect, get_object_or_404, render
from django.urls import reverse
from django.views import View
from django.views.generic import ListView, TemplateView, DetailView, FormView
from django.contrib.auth.views import LoginView as DjangoLoginView, LogoutView as DjangoLogoutView
from django.contrib.auth.mixins import UserPassesTestMixin
from restaurant.models import Category, MenuItem, Order, OrderItem, OrderFeedback
from restaurant.forms import CheckoutForm, OrderTrackingForm

logger = logging.getLogger(__name__)


class LandingView(View):
    def get(self, request, *args, **kwargs):
        return redirect(reverse("restaurant:menu"))


class MenuListView(ListView):
    model = MenuItem
    template_name = "restaurant/menu.html"
    context_object_name = "menu_items"

    def get_queryset(self):
        from django.db.models import Sum, OuterRef, Subquery, IntegerField
        from django.db.models.functions import Coalesce
        
        # Subquery to calculate the sum of completed order quantities for each menu item
        completed_qty_subquery = OrderItem.objects.filter(
            order__status="COMPLETED",
            menu_item=OuterRef('pk')
        ).values('menu_item').annotate(
            total_qty=Sum('quantity')
        ).values('total_qty')
        
        # Annotate each menu item with its completed quantity (defaulting to 0 if none)
        queryset = MenuItem.objects.all().select_related("category").annotate(
            completed_quantity=Coalesce(Subquery(completed_qty_subquery), 0, output_field=IntegerField())
        )
        
        # Preserve original server-side category filtering for backward compatibility and test validation
        category_id = self.request.GET.get("category")
        if category_id:
            try:
                category_id = int(category_id)
                if Category.objects.filter(id=category_id).exists():
                    queryset = queryset.filter(category_id=category_id)
            except ValueError:
                pass
                
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Calculate popular items from completed orders
        menu_items_list = list(self.get_queryset())
        popular_items = [item for item in menu_items_list if item.is_available and item.completed_quantity > 0]
        popular_items.sort(key=lambda x: (-x.completed_quantity, x.id))
        popular_ids = [item.id for item in popular_items[:3]]
        
        context["popular_ids"] = popular_ids
        context["featured_items"] = popular_items[:5]
        context["categories"] = Category.objects.all()
        
        # Keep active_category for fallback or template highlighting if page is loaded with URL param
        active_category = None
        category_id = self.request.GET.get("category")
        if category_id:
            try:
                category_id = int(category_id)
                active_category = Category.objects.filter(id=category_id).first()
            except ValueError:
                pass
        context["active_category"] = active_category
        return context


class CartView(TemplateView):
    template_name = "restaurant/cart.html"


def cart_sync(request):
    """
    Synchronizes the frontend localStorage cart with the Django session cart.
    Accepts POST requests only. Validates items and quantities against the database.
    """
    if request.method != "POST":
        return JsonResponse(
            {"success": False, "error": "Method Not Allowed. Only POST is allowed."},
            status=405
        )

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, TypeError):
        return JsonResponse(
            {"success": False, "error": "Malformed JSON payload."},
            status=400
        )

    if not isinstance(data, dict) or "items" not in data or not isinstance(data["items"], list):
        return JsonResponse(
            {"success": False, "error": "Invalid cart payload structure."},
            status=400
        )

    # Clean and merge duplicate IDs from input
    items_map = {}
    instructions_map = {}
    for item in data["items"]:
        if not isinstance(item, dict) or "id" not in item or "quantity" not in item:
            continue

        item_id = str(item["id"]).strip()
        qty = item["quantity"]
        instr = item.get("special_instructions", "")

        # Explicitly reject boolean quantities (since bool is a subclass of int in Python)
        if isinstance(qty, bool):
            continue

        if not isinstance(qty, int):
            continue

        if qty < 1:
            continue

        # Sanitize instructions
        if not isinstance(instr, str):
            instr = ""
        instr = instr.strip()[:250]

        # Merge quantities and cap at MAX_QUANTITY (20)
        if item_id in items_map:
            items_map[item_id] = min(items_map[item_id] + qty, 20)
            if instr:
                existing_instr = instructions_map.get(item_id, "")
                if existing_instr and instr not in existing_instr:
                    instructions_map[item_id] = f"{existing_instr}, {instr}"[:250]
                else:
                    instructions_map[item_id] = instr
        else:
            items_map[item_id] = min(qty, 20)
            instructions_map[item_id] = instr

    # Single DB query to fetch matching available MenuItems
    valid_menu_items = MenuItem.objects.filter(
        id__in=items_map.keys(),
        is_available=True
    ).select_related("category")

    menu_items_by_id = {str(item.id): item for item in valid_menu_items}

    # Construct the sanitized session cart representation and the client JSON response.
    # Preserve the order of first valid appearance from the submitted payload.
    sanitized_cart = {}
    response_items = []

    for item in data["items"]:
        if not isinstance(item, dict) or "id" not in item:
            continue
        item_id_str = str(item["id"]).strip()

        if item_id_str in menu_items_by_id and item_id_str not in sanitized_cart:
            item_obj = menu_items_by_id[item_id_str]
            qty = items_map[item_id_str]
            instr = instructions_map.get(item_id_str, "")

            sanitized_cart[item_id_str] = {
                "quantity": qty,
                "special_instructions": instr
            }
            response_items.append({
                "id": item_id_str,
                "name": item_obj.name,
                "price": f"{item_obj.price:.2f}",
                "quantity": qty,
                "special_instructions": instr
            })

    # Save to Django Session
    request.session["cart"] = sanitized_cart
    request.session.modified = True

    return JsonResponse({
        "success": True,
        "items": response_items
    })


class CartCheckoutView(FormView):
    template_name = "restaurant/checkout.html"
    form_class = CheckoutForm

    def dispatch(self, request, *args, **kwargs):
        # Retrieve and validate the session cart
        session_cart = request.session.get("cart", {})
        if not session_cart or not isinstance(session_cart, dict):
            messages.warning(request, "Your cart is empty. Add items before checkout.")
            return redirect("restaurant:cart")

        # Perform server-side revalidation of items
        self.validated_items = self._revalidate_cart(request, session_cart)
        if not self.validated_items:
            messages.warning(request, "Your cart contains no available items. Please update your cart.")
            return redirect("restaurant:cart")

        # Authoritative calculation of totals using Decimal
        self.subtotal, self.tax, self.grand_total = self._calculate_totals(self.validated_items)

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Expose summary calculations and items to the template
        context["checkout_items"] = self.validated_items
        context["subtotal"] = self.subtotal.quantize(Decimal("0.01"))
        context["tax"] = self.tax.quantize(Decimal("0.01"))
        context["grand_total"] = self.grand_total.quantize(Decimal("0.01"))
        return context

    def form_valid(self, form):
        # Retrieve form fields
        name = form.cleaned_data["customer_name"]
        phone = form.cleaned_data["customer_phone"]
        table_number = form.cleaned_data.get("table_number")

        try:
            with transaction.atomic():
                # Create the Order
                order = Order.objects.create(
                    customer_name=name,
                    customer_phone=phone,
                    table_number=table_number,
                    subtotal_amount=self.subtotal.quantize(Decimal("0.01")),
                    tax_amount=self.tax.quantize(Decimal("0.01")),
                    tax_rate=Decimal("0.0500"),
                    total_amount=self.grand_total.quantize(Decimal("0.01")),
                    status="RECEIVED"
                )

                # Create OrderItems with order-time historical prices and names preserved
                order_items_to_create = []
                for entry in self.validated_items:
                    order_items_to_create.append(
                        OrderItem(
                            order=order,
                            menu_item=entry["menu_item"],
                            quantity=entry["quantity"],
                            special_instructions=entry.get("special_instructions", ""),
                            price_at_order=entry["menu_item"].price,
                            item_name_at_order=entry["menu_item"].name,
                            category_name_at_order=entry["menu_item"].category.name if entry["menu_item"].category else "Unknown Category"
                        )
                    )
                OrderItem.objects.bulk_create(order_items_to_create)

                # Clear Django session cart only after database operations succeed
                self.request.session["cart"] = {}
                self.request.session.modified = True

                # Provide positive success message
                messages.success(self.request, "Order placed successfully!")
                
                # Store order success marker in session for page reload/stale cart protection
                self.request.session["last_order_token_success"] = str(order.tracking_token)
                
                logger.info(f"Order #{order.id} placed successfully with total amount {order.total_amount}.")
                return redirect("restaurant:order_success", tracking_token=order.tracking_token)

        except Exception as e:
            logger.error(f"Checkout database write failed: {e}")
            # Safe traceback protection - display a generic form error if database writing fails
            form.add_error(None, f"An error occurred while creating your order. Please try again.")
            return self.form_invalid(form)

    def _revalidate_cart(self, request, session_cart):
        """
        Revalidates each item in the session cart against the database.
        Returns a list of dictionaries with valid MenuItem objects and quantities.
        Syncs any invalid changes back to the Django session.
        """
        sanitized_cart = {}
        validated_items = []
        has_changes = False

        # Gather item IDs from session keys
        item_ids = []
        for key in session_cart.keys():
            try:
                item_ids.append(int(key))
            except ValueError:
                has_changes = True

        # Fetch matching available MenuItems from database in a single query
        menu_items = MenuItem.objects.filter(id__in=item_ids, is_available=True)
        menu_items_by_id = {str(item.id): item for item in menu_items}

        for item_id_str, details in session_cart.items():
            # Reject invalid structure, quantities, or unavailable items
            if not isinstance(details, dict) or "quantity" not in details:
                has_changes = True
                continue

            qty = details["quantity"]

            # Explicit rejection of boolean quantities
            if isinstance(qty, bool):
                has_changes = True
                continue

            if not isinstance(qty, int) or qty < 1:
                has_changes = True
                continue

            # Cap quantity at 20
            if qty > 20:
                qty = 20
                has_changes = True

            # Sanitize instructions
            instr = details.get("special_instructions", "")
            if not isinstance(instr, str):
                instr = ""
            instr = instr.strip()[:250]

            # If the item exists and is available in DB
            if item_id_str in menu_items_by_id:
                menu_item = menu_items_by_id[item_id_str]
                sanitized_cart[item_id_str] = {
                    "quantity": qty,
                    "special_instructions": instr
                }
                validated_items.append({
                    "menu_item": menu_item,
                    "quantity": qty,
                    "special_instructions": instr,
                    "line_total": menu_item.price * qty
                })
            else:
                has_changes = True

        # If any validation filters changed the cart, sync it back to request session
        if has_changes:
            request.session["cart"] = sanitized_cart
            request.session.modified = True
            messages.info(request, "Some unavailable items or incorrect quantities were updated in your cart.")

        return validated_items

    def _calculate_totals(self, validated_items):
        """
        Calculates subtotal, 5% tax, and grand total authoritatively using Decimal.
        """
        subtotal = Decimal("0.00")
        for entry in validated_items:
            subtotal += Decimal(str(entry["menu_item"].price)) * entry["quantity"]
        
        # 5% tax rate
        tax = subtotal * Decimal("0.05")
        grand_total = subtotal + tax
        return subtotal, tax, grand_total


class OrderSuccessView(DetailView):
    model = Order
    template_name = "restaurant/order_success.html"
    context_object_name = "order"
    slug_field = "tracking_token"
    slug_url_kwarg = "tracking_token"

    def get_queryset(self):
        # Optimize query by prefetching items
        return super().get_queryset().prefetch_related("items")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        order = self.object

        context["subtotal"] = order.subtotal_amount.quantize(Decimal("0.01"))
        context["tax"] = order.tax_amount.quantize(Decimal("0.01"))
        context["grand_total"] = order.total_amount.quantize(Decimal("0.01"))
        
        # Check if this success load was direct redirection or refresh
        last_success_token = self.request.session.get("last_order_token_success")
        if last_success_token == str(order.tracking_token):
            context["just_ordered"] = True
            # Clear success marker after reading once
            del self.request.session["last_order_token_success"]
        else:
            context["just_ordered"] = False

        return context


# --- KITCHEN WORKFLOW SECURITY AND ACCESS MIXINS ---

class KitchenRequiredMixin(UserPassesTestMixin):
    """
    Enforces that the user is logged in and belongs to the Kitchen Staff group
    (or is a superuser). Authenticated non-kitchen users receive HTTP 403 Forbidden.
    Unauthenticated users are redirected to the kitchen login page.
    """
    def test_func(self):
        return self.request.user.is_authenticated and (
            self.request.user.is_superuser or 
            self.request.user.groups.filter(name="Kitchen Staff").exists()
        )

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied("You are not authorized to view the kitchen console.")
        return redirect("restaurant:kitchen_login")


# --- KITCHEN WORKFLOW VIEWS ---

class KitchenLoginView(DjangoLoginView):
    template_name = "restaurant/kitchen_login.html"
    
    def form_valid(self, form):
        user = form.get_user()
        # Verify kitchen authorization
        is_kitchen = user.is_superuser or user.groups.filter(name="Kitchen Staff").exists()
        if not is_kitchen:
            form.add_error(None, "You are not authorized as kitchen staff.")
            return self.form_invalid(form)
        return super().form_valid(form)
        
    def get_success_url(self):
        return reverse("restaurant:kitchen_dashboard")


class KitchenLogoutView(DjangoLogoutView):
    def get_success_url(self):
        return reverse("restaurant:kitchen_login")


class KitchenDashboardView(KitchenRequiredMixin, ListView):
    model = Order
    template_name = "restaurant/kitchen_dashboard.html"
    context_object_name = "orders"

    def get_queryset(self):
        sort_by = self.request.GET.get("sort", "oldest")
        # Base query: active orders only
        queryset = Order.objects.exclude(status__in=["COMPLETED", "CANCELLED"]).prefetch_related("items__menu_item")
        
        if sort_by == "newest":
            return queryset.order_by("-created_at")
        elif sort_by == "priority":
            # Priority sort (URGENT -> PRIORITY -> NORMAL)
            priority_map = {"URGENT": 1, "PRIORITY": 2, "NORMAL": 3}
            orders_list = list(queryset)
            orders_list.sort(key=lambda o: (priority_map.get(o.priority, 4), o.created_at))
            return orders_list
        elif sort_by == "delayed":
            # Delayed first, then oldest first
            orders_list = list(queryset)
            orders_list.sort(key=lambda o: (0 if o.is_delayed else 1, o.created_at))
            return orders_list
        else:
            return queryset.order_by("created_at")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        orders = self.get_queryset()
        
        # Group active orders into status workflows
        context["received_orders"] = [o for o in orders if o.status == "RECEIVED"]
        context["preparing_orders"] = [o for o in orders if o.status == "PREPARING"]
        context["ready_orders"] = [o for o in orders if o.status == "READY"]
        context["current_sort"] = self.request.GET.get("sort", "oldest")
        return context


class KitchenOrderDetailView(KitchenRequiredMixin, DetailView):
    model = Order
    template_name = "restaurant/kitchen_order_detail.html"
    context_object_name = "order"

    def get_queryset(self):
        # Optimize query for related items display
        return Order.objects.prefetch_related("items__menu_item")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        order = self.object
        
        # Calculation from historical pricing records
        subtotal = sum(item.price_at_order * item.quantity for item in order.items.all())
        tax = subtotal * Decimal("0.05")
        
        context["subtotal"] = subtotal.quantize(Decimal("0.01"))
        context["tax"] = tax.quantize(Decimal("0.01"))
        context["grand_total"] = order.total_amount.quantize(Decimal("0.01"))
        
        # Setup valid next step actions
        ALLOWED_STATUS_TRANSITIONS = {
            "RECEIVED": "PREPARING",
            "PREPARING": "READY",
            "READY": "COMPLETED"
        }
        context["next_status"] = ALLOWED_STATUS_TRANSITIONS.get(order.status)
        return context


ALLOWED_STATUS_TRANSITIONS = {
    "RECEIVED": "PREPARING",
    "PREPARING": "READY",
    "READY": "COMPLETED"
}

class KitchenOrderStatusUpdateView(KitchenRequiredMixin, View):
    """
    Enforces sequential status transitions for active orders, and supports
    editing priority or prep time by authorized staff.
    Accepts POST requests only. Uses transaction locks to prevent concurrency bypasses.
    """
    def post(self, request, pk, *args, **kwargs):
        action = request.POST.get("action")
        
        with transaction.atomic():
            # Apply row-level locks
            order = Order.objects.select_for_update().filter(id=pk).first()
            if not order:
                logger.error(f"Kitchen operation failed: Order ID {pk} not found.")
                messages.error(request, "Requested order not found.")
                return redirect("restaurant:kitchen_dashboard")

            if action == "priority":
                new_priority = request.POST.get("priority")
                if new_priority in ["NORMAL", "PRIORITY", "URGENT"]:
                    old_priority = order.priority
                    order.priority = new_priority
                    order.save(update_fields=["priority"])
                    
                    from restaurant.models import AuditLog
                    AuditLog.objects.create(
                        actor=request.user,
                        action="PRIORITY_CHANGE",
                        target_type="Order",
                        target_id=str(order.id),
                        description=f"Changed Order #{order.id} priority from {old_priority} to {new_priority}."
                    )
                    
                    logger.info(f"Order #{order.id} priority updated from {old_priority} to {new_priority} by user {request.user.username}.")
                    messages.success(request, f"Order #{order.id} priority updated to {new_priority}.")
                else:
                    messages.error(request, "Invalid priority choice.")
                return redirect("restaurant:kitchen_order_detail", pk=order.id)

            elif action == "prep_time":
                prep_val = request.POST.get("estimated_preparation_minutes")
                old_prep = order.estimated_preparation_minutes
                if not prep_val or prep_val.strip() == "":
                    order.estimated_preparation_minutes = None
                    order.save(update_fields=["estimated_preparation_minutes"])
                    
                    from restaurant.models import AuditLog
                    AuditLog.objects.create(
                        actor=request.user,
                        action="PREP_TIME_CHANGE",
                        target_type="Order",
                        target_id=str(order.id),
                        description=f"Cleared estimated preparation time for Order #{order.id}."
                    )
                    
                    messages.success(request, f"Cleared preparation time for Order #{order.id}.")
                else:
                    try:
                        prep_minutes = int(prep_val)
                        if 5 <= prep_minutes <= 180:
                            order.estimated_preparation_minutes = prep_minutes
                            order.save(update_fields=["estimated_preparation_minutes"])
                            
                            from restaurant.models import AuditLog
                            AuditLog.objects.create(
                                actor=request.user,
                                action="PREP_TIME_CHANGE",
                                target_type="Order",
                                target_id=str(order.id),
                                description=f"Updated estimated preparation time for Order #{order.id} to {prep_minutes} minutes."
                            )
                            
                            logger.info(f"Order #{order.id} prep minutes updated from {old_prep} to {prep_minutes} by user {request.user.username}.")
                            messages.success(request, f"Order #{order.id} preparation time set to {prep_minutes} minutes.")
                        else:
                            messages.error(request, "Estimated preparation time must be between 5 and 180 minutes.")
                    except ValueError:
                        messages.error(request, "Preparation time must be a valid integer.")
                return redirect("restaurant:kitchen_order_detail", pk=order.id)

            else:
                requested_status = request.POST.get("status")
                current_status = order.status
                expected_next = ALLOWED_STATUS_TRANSITIONS.get(current_status)

                if requested_status != expected_next:
                    logger.warning(
                        f"Invalid status transition attempted: Order #{order.id} is in status {current_status}, "
                        f"tried to transition to {requested_status}."
                    )
                    messages.error(
                        request,
                        f"Transition from {order.get_status_display()} to {requested_status or 'None'} is invalid."
                    )
                    return redirect("restaurant:kitchen_order_detail", pk=order.id)

                # Transition is valid -> save state
                order.status = requested_status
                if requested_status == "COMPLETED":
                    from django.utils import timezone
                    order.completed_at = timezone.now()
                    order.save(update_fields=["status", "completed_at"])
                else:
                    order.save(update_fields=["status"])
                
                logger.info(f"Order #{order.id} status updated successfully from {current_status} to {requested_status} by kitchen user {request.user.username}.")
                messages.success(
                    request,
                    f"Order #{order.id} status updated to {order.get_status_display()}."
                )

        return redirect("restaurant:kitchen_dashboard")

    def get(self, request, *args, **kwargs):
        from django.http import HttpResponseNotAllowed
        return HttpResponseNotAllowed(["POST"])


class OrderTrackingView(FormView):
    template_name = "restaurant/order_tracking.html"
    form_class = OrderTrackingForm

    def form_valid(self, form):
        tracking_token = form.cleaned_data["tracking_token"]
        # Verify order exists
        if not Order.objects.filter(tracking_token=tracking_token).exists():
            form.add_error(None, "No order was found with that Tracking ID.")
            return self.form_invalid(form)
        return redirect("restaurant:order_tracking_detail", tracking_token=tracking_token)


def order_again_lookup(request):
    if request.method == "POST":
        phone = request.POST.get("phone", "").strip()
        if not phone:
            messages.error(request, "Please enter a valid phone number.")
            return redirect("restaurant:order_tracking")
            
        past_orders = Order.objects.filter(customer_phone=phone).order_by("-created_at")
        if not past_orders.exists():
            messages.error(request, f"No past orders found for {phone}.")
            return redirect("restaurant:order_tracking")
            
        return render(request, "restaurant/order_again_list.html", {"orders": past_orders, "phone": phone})
    
    return redirect("restaurant:order_tracking")


class OrderTrackingDetailView(DetailView):
    model = Order
    template_name = "restaurant/order_tracking_detail.html"
    context_object_name = "order"
    slug_field = "tracking_token"
    slug_url_kwarg = "tracking_token"

    def get_queryset(self):
        return Order.objects.prefetch_related("items")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        order = self.object
        
        context["subtotal"] = order.subtotal_amount.quantize(Decimal("0.01"))
        context["tax"] = order.tax_amount.quantize(Decimal("0.01"))
        context["grand_total"] = order.total_amount.quantize(Decimal("0.01"))
        return context


class OrderTrackingStatusView(View):
    """
    Status JSON Endpoint: Returns raw status, human-readable status, and is_completed value.
    Accepts GET requests only.
    """
    def get(self, request, tracking_token, *args, **kwargs):
        order = Order.objects.filter(tracking_token=tracking_token).first()
        if not order:
            return JsonResponse(
                {"success": False, "error": "Order not found."},
                status=404
            )
        
        is_completed = order.status == "COMPLETED"
        is_cancelled = order.status == "CANCELLED"
        is_terminal = is_completed or is_cancelled
        
        estimated_ready_time = None
        if order.estimated_preparation_minutes:
            from django.utils import timezone
            import datetime
            ready_dt = order.created_at + datetime.timedelta(minutes=order.estimated_preparation_minutes)
            local_ready_dt = timezone.localtime(ready_dt)
            estimated_ready_time = local_ready_dt.strftime("%I:%M %p")

        response = JsonResponse({
            "success": True,
            "tracking_token": str(order.tracking_token),
            "status": order.status,
            "status_display": order.get_status_display(),
            "is_completed": is_completed,
            "is_cancelled": is_cancelled,
            "is_terminal": is_terminal,
            "is_delayed": order.is_delayed,
            "estimated_prep_minutes": order.estimated_preparation_minutes,
            "estimated_ready_time": estimated_ready_time
        })
        response["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        return response

    def post(self, request, *args, **kwargs):
        from django.http import HttpResponseNotAllowed
        return HttpResponseNotAllowed(["GET"])


# --- MANAGER DASHBOARD & OPERATIONS ---

import datetime
from django.utils import timezone
from django.db.models import Sum, Count, Avg, F, Q
from django.db.models.functions import Coalesce
from django.contrib.auth import logout
from django.urls import reverse_lazy
from django.core.exceptions import PermissionDenied
from django.views.generic.edit import CreateView, UpdateView
from restaurant.forms import DateRangeFilterForm, MenuItemForm, CategoryForm

class ManagerRequiredMixin(UserPassesTestMixin):
    """
    Enforces that the user is authenticated and is either a superuser 
    or belongs to the 'Managers' group.
    """
    def test_func(self):
        return self.request.user.is_authenticated and (
            self.request.user.is_superuser or 
            self.request.user.groups.filter(name="Managers").exists()
        )
    
    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return redirect("restaurant:manager_login")
        raise PermissionDenied("You are not authorized to view the manager console.")


class ManagerLoginView(DjangoLoginView):
    template_name = "restaurant/manager_login.html"
    
    def form_valid(self, form):
        user = form.get_user()
        # Verify manager authorization
        is_manager = user.is_superuser or user.groups.filter(name="Managers").exists()
        if not is_manager:
            form.add_error(None, "You are not authorized as a restaurant manager.")
            return self.form_invalid(form)
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy("restaurant:manager_dashboard")


class ManagerLogoutView(View):
    def post(self, request, *args, **kwargs):
        logout(request)
        messages.success(request, "Logged out successfully.")
        return redirect("restaurant:manager_login")

    def get(self, request, *args, **kwargs):
        from django.http import HttpResponseNotAllowed
        return HttpResponseNotAllowed(["POST"])


class ManagerDashboardView(ManagerRequiredMixin, TemplateView):
    template_name = "restaurant/manager_dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Validate date range filter form
        form = DateRangeFilterForm(self.request.GET)
        range_type = "today"
        start_date = None
        end_date = None
        if form.is_valid():
            range_type = form.cleaned_data.get("range") or "today"
            start_date = form.cleaned_data.get("start")
            end_date = form.cleaned_data.get("end")
        else:
            form = DateRangeFilterForm(initial={"range": "today"})
            
        today = timezone.localdate()
        
        if range_type == "today":
            start_dt = timezone.make_aware(datetime.datetime.combine(today, datetime.time.min))
            end_dt = timezone.make_aware(datetime.datetime.combine(today, datetime.time.max))
        elif range_type == "7d":
            start_day = today - datetime.timedelta(days=7)
            start_dt = timezone.make_aware(datetime.datetime.combine(start_day, datetime.time.min))
            end_dt = timezone.make_aware(datetime.datetime.combine(today, datetime.time.max))
        elif range_type == "30d":
            start_day = today - datetime.timedelta(days=30)
            start_dt = timezone.make_aware(datetime.datetime.combine(start_day, datetime.time.min))
            end_dt = timezone.make_aware(datetime.datetime.combine(today, datetime.time.max))
        elif range_type == "custom" and start_date and end_date:
            start_dt = timezone.make_aware(datetime.datetime.combine(start_date, datetime.time.min))
            end_dt = timezone.make_aware(datetime.datetime.combine(end_date, datetime.time.max))
        else:
            range_type = "today"
            start_dt = timezone.make_aware(datetime.datetime.combine(today, datetime.time.min))
            end_dt = timezone.make_aware(datetime.datetime.combine(today, datetime.time.max))
            
        # Orders within selected date range
        orders_in_range = Order.objects.filter(created_at__range=(start_dt, end_dt))
        
        total_orders_count = orders_in_range.count()
        
        # Order counts grouped by status
        status_counts = orders_in_range.aggregate(
            received=Count("id", filter=Q(status="RECEIVED")),
            preparing=Count("id", filter=Q(status="PREPARING")),
            ready=Count("id", filter=Q(status="READY")),
            completed=Count("id", filter=Q(status="COMPLETED")),
            cancelled=Count("id", filter=Q(status="CANCELLED")),
        )
        
        # Realized revenue is from status COMPLETED only
        completed_orders = orders_in_range.filter(status="COMPLETED")
        completed_revenue = completed_orders.aggregate(total=Coalesce(Sum("total_amount"), Decimal("0.00")))["total"]
        completed_count = completed_orders.count()
        
        # Average Order Value using completed orders
        if completed_count > 0:
            avg_order_value = (completed_revenue / completed_count).quantize(Decimal("0.01"))
        else:
            avg_order_value = Decimal("0.00")
            
        # Recent Orders (limit 5)
        recent_orders = orders_in_range.order_by("-created_at")[:5]
        
        # Top 5 items based on historical snapshot item_name_at_order on completed orders in range
        top_items = OrderItem.objects.filter(
            order__created_at__range=(start_dt, end_dt),
            order__status="COMPLETED"
        ).values("item_name_at_order").annotate(
            total_quantity=Sum("quantity"),
            total_revenue=Sum(F("price_at_order") * F("quantity"))
        ).order_by("-total_quantity")[:5]
        
        # Category Performance on completed orders
        category_perf = OrderItem.objects.filter(
            order__created_at__range=(start_dt, end_dt),
            order__status="COMPLETED"
        ).values("category_name_at_order").annotate(
            total_quantity=Sum("quantity"),
            total_revenue=Sum(F("price_at_order") * F("quantity"))
        ).order_by("-total_revenue")
        
        # Cancellation rate: (Cancelled / Total) * 100
        cancelled_count = status_counts["cancelled"] or 0
        if total_orders_count > 0:
            cancellation_rate = round((cancelled_count / total_orders_count) * 100, 1)
        else:
            cancellation_rate = 0.0

        # Average Completion Time
        completed_with_time = completed_orders.filter(completed_at__isnull=False)
        avg_completion = completed_with_time.annotate(
            duration=F("completed_at") - F("created_at")
        ).aggregate(Avg("duration"))["duration__avg"]

        if avg_completion:
            total_seconds = avg_completion.total_seconds()
            avg_completion_minutes = round(total_seconds / 60, 1)
        else:
            avg_completion_minutes = 0.0

        # Average Rating from OrderFeedback within the selected range
        avg_rating_agg = OrderFeedback.objects.filter(
            order__created_at__range=(start_dt, end_dt)
        ).aggregate(Avg('rating'))
        average_rating = avg_rating_agg['rating__avg']

        context.update({
            "filter_form": form,
            "range_type": range_type,
            "total_orders": total_orders_count,
            "completed_revenue": completed_revenue,
            "avg_order_value": avg_order_value,
            "status_counts": status_counts,
            "recent_orders": recent_orders,
            "top_items": top_items,
            "category_performance": category_perf,
            "cancellation_rate": cancellation_rate,
            "avg_completion_minutes": avg_completion_minutes,
            "average_rating": average_rating,
            "start_dt_str": start_dt.strftime("%Y-%m-%d"),
            "end_dt_str": end_dt.strftime("%Y-%m-%d"),
        })
import csv
from django.http import HttpResponse
from restaurant.models import AuditLog

class ManagerCSVExportView(ManagerRequiredMixin, View):
    """
    Exports filtered order records within a date range to a CSV file.
    Enforces spreadsheet formula injection protection.
    """
    def get(self, request, *args, **kwargs):
        range_type = request.GET.get("range", "today")
        start_str = request.GET.get("start")
        end_str = request.GET.get("end")
        
        today = timezone.localdate()
        
        if range_type == "today":
            start_dt = timezone.make_aware(datetime.datetime.combine(today, datetime.time.min))
            end_dt = timezone.make_aware(datetime.datetime.combine(today, datetime.time.max))
        elif range_type == "7d":
            start_day = today - datetime.timedelta(days=7)
            start_dt = timezone.make_aware(datetime.datetime.combine(start_day, datetime.time.min))
            end_dt = timezone.make_aware(datetime.datetime.combine(today, datetime.time.max))
        elif range_type == "30d":
            start_day = today - datetime.timedelta(days=30)
            start_dt = timezone.make_aware(datetime.datetime.combine(start_day, datetime.time.min))
            end_dt = timezone.make_aware(datetime.datetime.combine(today, datetime.time.max))
        elif range_type == "custom" and start_str and end_str:
            try:
                start_date = datetime.datetime.strptime(start_str, "%Y-%m-%d").date()
                end_date = datetime.datetime.strptime(end_str, "%Y-%m-%d").date()
                start_dt = timezone.make_aware(datetime.datetime.combine(start_date, datetime.time.min))
                end_dt = timezone.make_aware(datetime.datetime.combine(end_date, datetime.time.max))
            except ValueError:
                start_dt = timezone.make_aware(datetime.datetime.combine(today, datetime.time.min))
                end_dt = timezone.make_aware(datetime.datetime.combine(today, datetime.time.max))
        else:
            start_dt = timezone.make_aware(datetime.datetime.combine(today, datetime.time.min))
            end_dt = timezone.make_aware(datetime.datetime.combine(today, datetime.time.max))
            
        orders = Order.objects.filter(created_at__range=(start_dt, end_dt)).order_by("-created_at")
        
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        filename = f"orders_analytics_{start_dt.strftime('%Y-%m-%d')}_to_{end_dt.strftime('%Y-%m-%d')}.csv"
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        
        response.write(b'\xef\xbb\xbf')
        
        writer = csv.writer(response)
        writer.writerow([
            "Order ID", "Customer Name", "Customer Phone", "Table Number", 
            "Created At", "Completed At", "Status", "Priority", 
            "Subtotal (INR)", "Tax (INR)", "Grand Total (INR)"
        ])
        
        def escape_csv(val):
            if val is None:
                return ""
            s = str(val)
            if s and s[0] in ['=', '+', '-', '@']:
                return "'" + s
            return s
            
        for order in orders:
            completed_str = timezone.localtime(order.completed_at).strftime("%Y-%m-%d %H:%M:%S") if order.completed_at else "N/A"
            created_str = timezone.localtime(order.created_at).strftime("%Y-%m-%d %H:%M:%S")
            
            writer.writerow([
                escape_csv(order.id),
                escape_csv(order.customer_name),
                escape_csv(order.customer_phone),
                escape_csv(order.table_number if order.table_number else "Takeaway"),
                escape_csv(created_str),
                escape_csv(completed_str),
                escape_csv(order.get_status_display()),
                escape_csv(order.get_priority_display()),
                escape_csv(order.subtotal_amount),
                escape_csv(order.tax_amount),
                escape_csv(order.total_amount)
            ])
            
        return response


class ManagerAuditLogListView(ManagerRequiredMixin, ListView):
    model = AuditLog
    template_name = "restaurant/manager_audit_logs.html"
    context_object_name = "audit_logs"
    paginate_by = 25

    def get_queryset(self):
        return AuditLog.objects.all().select_related("actor").order_by("-timestamp")


class ManagerOrderListView(ManagerRequiredMixin, ListView):
    model = Order
    template_name = "restaurant/manager_order_list.html"
    context_object_name = "orders"
    paginate_by = 20

    def get_queryset(self):
        queryset = Order.objects.all()
        
        # Filter by status
        status = self.request.GET.get("status")
        if status in [c[0] for c in Order.STATUS_CHOICES]:
            queryset = queryset.filter(status=status)
            
        # Filter by date range
        range_type = self.request.GET.get("range", "today")
        today = timezone.localdate()
        
        if range_type == "today":
            start_dt = timezone.make_aware(datetime.datetime.combine(today, datetime.time.min))
            end_dt = timezone.make_aware(datetime.datetime.combine(today, datetime.time.max))
            queryset = queryset.filter(created_at__range=(start_dt, end_dt))
        elif range_type == "7d":
            start_day = today - datetime.timedelta(days=7)
            start_dt = timezone.make_aware(datetime.datetime.combine(start_day, datetime.time.min))
            end_dt = timezone.make_aware(datetime.datetime.combine(today, datetime.time.max))
            queryset = queryset.filter(created_at__range=(start_dt, end_dt))
        elif range_type == "30d":
            start_day = today - datetime.timedelta(days=30)
            start_dt = timezone.make_aware(datetime.datetime.combine(start_day, datetime.time.min))
            end_dt = timezone.make_aware(datetime.datetime.combine(today, datetime.time.max))
            queryset = queryset.filter(created_at__range=(start_dt, end_dt))
        elif range_type == "custom":
            start_str = self.request.GET.get("start")
            end_str = self.request.GET.get("end")
            if start_str and end_str:
                try:
                    start_date = datetime.datetime.strptime(start_str, "%Y-%m-%d").date()
                    end_date = datetime.datetime.strptime(end_str, "%Y-%m-%d").date()
                    start_dt = timezone.make_aware(datetime.datetime.combine(start_date, datetime.time.min))
                    end_dt = timezone.make_aware(datetime.datetime.combine(end_date, datetime.time.max))
                    queryset = queryset.filter(created_at__range=(start_dt, end_dt))
                except ValueError:
                    pass
        
        return queryset.order_by("-created_at")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["status_choices"] = Order.STATUS_CHOICES
        context["current_status"] = self.request.GET.get("status", "")
        context["current_range"] = self.request.GET.get("range", "today")
        context["start_date"] = self.request.GET.get("start", "")
        context["end_date"] = self.request.GET.get("end", "")
        
        params = self.request.GET.copy()
        if "page" in params:
            del params["page"]
        context["query_params"] = params.urlencode()
        return context


class ManagerOrderDetailView(ManagerRequiredMixin, DetailView):
    model = Order
    template_name = "restaurant/manager_order_detail.html"
    context_object_name = "order"

    def get_queryset(self):
        return Order.objects.prefetch_related("items")


class ManagerOrderCancelView(ManagerRequiredMixin, View):
    def post(self, request, pk, *args, **kwargs):
        try:
            with transaction.atomic():
                order = Order.objects.select_for_update().get(pk=pk)
                if order.status != "RECEIVED":
                    logger.warning(f"Order cancellation failed: Order #{order.id} is in status {order.status}, not RECEIVED.")
                    messages.error(request, "Only orders with RECEIVED status can be cancelled.")
                    return redirect("restaurant:manager_order_detail", pk=pk)
                
                order.status = "CANCELLED"
                order.save()
                
                from restaurant.models import AuditLog
                AuditLog.objects.create(
                    actor=request.user,
                    action="ORDER_CANCEL",
                    target_type="Order",
                    target_id=str(order.id),
                    description=f"Cancelled Order #{order.id}."
                )
                
                logger.info(f"Order #{order.id} was successfully cancelled by manager {request.user.username}.")
                messages.success(request, f"Order #{order.id} was successfully cancelled.")
        except Order.DoesNotExist:
            logger.error(f"Order cancellation failed: Order ID {pk} does not exist.")
            messages.error(request, "Order not found.")
            return redirect("restaurant:manager_dashboard")
        return redirect("restaurant:manager_order_detail", pk=pk)

    def get(self, request, *args, **kwargs):
        from django.http import HttpResponseNotAllowed
        return HttpResponseNotAllowed(["POST"])


class ManagerMenuItemListView(ManagerRequiredMixin, ListView):
    model = MenuItem
    template_name = "restaurant/manager_menu_list.html"
    context_object_name = "menu_items"
    paginate_by = 25

    def get_queryset(self):
        queryset = MenuItem.objects.all().select_related("category")
        category_id = self.request.GET.get("category")
        if category_id:
            try:
                queryset = queryset.filter(category_id=int(category_id))
            except ValueError:
                pass
        return queryset.order_by("category__name", "name")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["categories"] = Category.objects.all()
        context["current_category"] = self.request.GET.get("category", "")
        
        params = self.request.GET.copy()
        if "page" in params:
            del params["page"]
        context["query_params"] = params.urlencode()
        return context


class ManagerMenuItemCreateView(ManagerRequiredMixin, CreateView):
    model = MenuItem
    form_class = MenuItemForm
    template_name = "restaurant/manager_menu_form.html"
    success_url = reverse_lazy("restaurant:manager_menu_list")

    def form_valid(self, form):
        response = super().form_valid(form)
        from restaurant.models import AuditLog
        AuditLog.objects.create(
            actor=self.request.user,
            action="MENU_ITEM_CREATE",
            target_type="MenuItem",
            target_id=str(self.object.id),
            description=f"Created menu item '{self.object.name}' (Price: ₹{self.object.price})."
        )
        messages.success(self.request, "Menu item added successfully.")
        return response


class ManagerMenuItemUpdateView(ManagerRequiredMixin, UpdateView):
    model = MenuItem
    form_class = MenuItemForm
    template_name = "restaurant/manager_menu_form.html"
    success_url = reverse_lazy("restaurant:manager_menu_list")

    def form_valid(self, form):
        response = super().form_valid(form)
        from restaurant.models import AuditLog
        AuditLog.objects.create(
            actor=self.request.user,
            action="MENU_ITEM_UPDATE",
            target_type="MenuItem",
            target_id=str(self.object.id),
            description=f"Updated menu item '{self.object.name}'."
        )
        messages.success(self.request, "Menu item updated successfully.")
        return response


class ManagerMenuItemAvailabilityView(ManagerRequiredMixin, View):
    def post(self, request, pk, *args, **kwargs):
        try:
            item = MenuItem.objects.get(pk=pk)
            item.is_available = not item.is_available
            item.save()
            status_str = "available" if item.is_available else "unavailable"
            
            from restaurant.models import AuditLog
            AuditLog.objects.create(
                actor=request.user,
                action="MENU_ITEM_AVAILABILITY",
                target_type="MenuItem",
                target_id=str(item.id),
                description=f"Toggled availability of '{item.name}' to {status_str}."
            )
            
            messages.success(request, f"Menu item '{item.name}' is now marked {status_str}.")
        except MenuItem.DoesNotExist:
            messages.error(request, "Menu item not found.")
        return redirect("restaurant:manager_menu_list")

    def get(self, request, *args, **kwargs):
        from django.http import HttpResponseNotAllowed
        return HttpResponseNotAllowed(["POST"])


class ManagerCategoryListView(ManagerRequiredMixin, ListView):
    model = Category
    template_name = "restaurant/manager_category_list.html"
    context_object_name = "categories"

    def get_queryset(self):
        return Category.objects.all().order_by("name")


class ManagerCategoryCreateView(ManagerRequiredMixin, CreateView):
    model = Category
    form_class = CategoryForm
    template_name = "restaurant/manager_category_form.html"
    success_url = reverse_lazy("restaurant:manager_category_list")

    def form_valid(self, form):
        response = super().form_valid(form)
        from restaurant.models import AuditLog
        AuditLog.objects.create(
            actor=self.request.user,
            action="CATEGORY_CREATE",
            target_type="Category",
            target_id=str(self.object.id),
            description=f"Created category '{self.object.name}'."
        )
        messages.success(self.request, "Category created successfully.")
        return response


class ManagerCategoryUpdateView(ManagerRequiredMixin, UpdateView):
    model = Category
    form_class = CategoryForm
    template_name = "restaurant/manager_category_form.html"
    success_url = reverse_lazy("restaurant:manager_category_list")

    def form_valid(self, form):
        response = super().form_valid(form)
        from restaurant.models import AuditLog
        AuditLog.objects.create(
            actor=self.request.user,
            action="CATEGORY_UPDATE",
            target_type="Category",
            target_id=str(self.object.id),
            description=f"Updated category '{self.object.name}'."
        )
        messages.success(self.request, "Category updated successfully.")
        return response


class OrderReceiptView(DetailView):
    model = Order
    template_name = "restaurant/order_receipt.html"
    context_object_name = "order"
    slug_field = "tracking_token"
    slug_url_kwarg = "tracking_token"

    def get_queryset(self):
        return Order.objects.prefetch_related("items")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        order = self.object
        context["subtotal"] = order.subtotal_amount.quantize(Decimal("0.01"))
        context["tax"] = order.tax_amount.quantize(Decimal("0.01"))
        context["grand_total"] = order.total_amount.quantize(Decimal("0.01"))
        return context


def download_receipt_pdf(request, tracking_token):
    order = get_object_or_404(Order.objects.prefetch_related("items"), tracking_token=tracking_token)
    
    # We use the same context as OrderReceiptView
    context = {
        "order": order,
        "subtotal": order.subtotal_amount.quantize(Decimal("0.01")),
        "tax": order.tax_amount.quantize(Decimal("0.01")),
        "grand_total": order.total_amount.quantize(Decimal("0.01")),
    }
    
    html_string = render_to_string("restaurant/order_receipt.html", context)
    
    # Generate PDF
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="receipt_{order.id}.pdf"'
    
    try:
        from xhtml2pdf import pisa
        pisa_status = pisa.CreatePDF(html_string, dest=response)
        if pisa_status.err:
            return HttpResponse("Error generating PDF", status=500)
    except ImportError:
        return HttpResponse("PDF generation library is not installed.", status=500)
        
    return response


def submit_order_feedback(request, tracking_token):
    if request.method == "POST":
        order = get_object_or_404(Order, tracking_token=tracking_token)
        if order.status != "COMPLETED":
            messages.error(request, "Feedback can only be submitted for completed orders.")
            return redirect("restaurant:order_tracking_status", tracking_token=tracking_token)
            
        rating = request.POST.get("rating")
        comment = request.POST.get("comment", "")
        
        try:
            rating = int(rating)
            if 1 <= rating <= 5:
                # Update or create
                OrderFeedback.objects.update_or_create(
                    order=order,
                    defaults={'rating': rating, 'comment': comment}
                )
                messages.success(request, "Thank you for your feedback!")
            else:
                messages.error(request, "Invalid rating value.")
        except (ValueError, TypeError):
            messages.error(request, "Invalid rating value.")
            
    return redirect("restaurant:order_tracking_status", tracking_token=tracking_token)


class ManagerOrderReceiptView(ManagerRequiredMixin, DetailView):
    model = Order
    template_name = "restaurant/order_receipt.html"
    context_object_name = "order"

    def get_queryset(self):
        return Order.objects.prefetch_related("items")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        order = self.object
        context["subtotal"] = order.subtotal_amount.quantize(Decimal("0.01"))
        context["tax"] = order.tax_amount.quantize(Decimal("0.01"))
        context["grand_total"] = order.total_amount.quantize(Decimal("0.01"))
        context["is_manager"] = True
        return context


class StaffAccessView(TemplateView):
    template_name = "restaurant/staff_access.html"

