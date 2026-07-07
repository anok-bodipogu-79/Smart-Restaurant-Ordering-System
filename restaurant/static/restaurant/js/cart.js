"use strict";

// Shopping Cart Configuration
const CART_STORAGE_KEY = "restaurantCart";
const TAX_RATE = 0.05;
const MAX_QUANTITY = 20;

// Tracking sequence number for race condition prevention
let currentSyncSequence = 0;

// Read cart from localStorage defensively
function getCart() {
    const rawData = localStorage.getItem(CART_STORAGE_KEY);
    if (!rawData) {
        return [];
    }

    try {
        const cart = JSON.parse(rawData);
        if (!Array.isArray(cart)) {
            localStorage.removeItem(CART_STORAGE_KEY);
            return [];
        }

        // Validate and clean each item
        const cleanedCart = [];
        const seenIds = new Set();

        for (const item of cart) {
            if (item && typeof item === "object" && item.id && item.name) {
                const id = String(item.id).trim();
                const name = String(item.name).trim();
                const price = parseFloat(item.price);
                let quantity = parseInt(item.quantity, 10);

                if (!isNaN(price) && price > 0 && !isNaN(quantity) && quantity >= 1) {
                    // Enforce quantity cap
                    if (quantity > MAX_QUANTITY) {
                        quantity = MAX_QUANTITY;
                    }

                    if (seenIds.has(id)) {
                        // Merge duplicate IDs if present
                        const existingItem = cleanedCart.find(i => i.id === id);
                        if (existingItem) {
                            existingItem.quantity = Math.min(existingItem.quantity + quantity, MAX_QUANTITY);
                        }
                    } else {
                        seenIds.add(id);
                        cleanedCart.push({ id, name, price, quantity });
                    }
                }
            }
        }

        // If validation cleaned/changed the cart, update storage
        if (cleanedCart.length !== cart.length) {
            localStorage.setItem(CART_STORAGE_KEY, JSON.stringify(cleanedCart));
        }

        return cleanedCart;
    } catch (e) {
        console.error("Error parsing cart from localStorage. Resetting cart.", e);
        localStorage.removeItem(CART_STORAGE_KEY);
        return [];
    }
}

// Save cart to localStorage, update navigation badge, and synchronize with server
function saveCart(cart) {
    localStorage.setItem(CART_STORAGE_KEY, JSON.stringify(cart));
    updateCartCount(cart);
    synchronizeCartWithServer();
}

// Update the navigation cart count badge
function updateCartCount(cart) {
    const cartCountElement = document.getElementById("cart-count");
    if (!cartCountElement) return;

    const totalUnits = cart.reduce((sum, item) => sum + item.quantity, 0);
    cartCountElement.textContent = String(totalUnits);
}

// Synchronize frontend cart with Django Session cart backend
function synchronizeCartWithServer() {
    const cart = getCart();
    
    // Transform cart to only send ID and quantity to the server.
    // The server does not trust browser-calculated names, prices, or totals.
    const payload = {
        items: cart.map(item => ({
            id: item.id,
            quantity: item.quantity
        }))
    };

    const csrfTokenMeta = document.querySelector('meta[name="csrf-token"]');
    const csrfToken = csrfTokenMeta ? csrfTokenMeta.getAttribute("content") : "";
    const syncUrl = document.body.dataset.cartSyncUrl;

    if (!syncUrl) {
        console.warn("Cart synchronization URL not specified in document body attributes.");
        return;
    }

    const sequenceId = ++currentSyncSequence;

    fetch(syncUrl, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": csrfToken
        },
        body: JSON.stringify(payload)
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP synchronization status code error: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        // Prevent older synchronization requests from overwriting newer cart states
        if (sequenceId !== currentSyncSequence) {
            return;
        }

        if (data.success) {
            // Reconcile browser cart items with validated server database items
            // This replaces names and prices with trusted values from the server
            const reconciledCart = data.items.map(item => ({
                id: String(item.id),
                name: item.name,
                price: parseFloat(item.price),
                quantity: item.quantity
            }));

            // Save reconciled data directly to localStorage to avoid infinite recursion
            localStorage.setItem(CART_STORAGE_KEY, JSON.stringify(reconciledCart));
            updateCartCount(reconciledCart);
            renderCartPage();
        } else {
            console.error("Cart synchronization rejected by server:", data.error);
        }
    })
    .catch(error => {
        console.error("Cart synchronization network error. Retaining local cart states.", error);
    });
}

// Add an item to the cart from the menu page
function addItemToCart(id, name, price) {
    const cart = getCart();
    const existingItem = cart.find(item => item.id === id);

    if (existingItem) {
        if (existingItem.quantity < MAX_QUANTITY) {
            existingItem.quantity += 1;
            saveCart(cart);
            showButtonFeedback(id, "Added");
        } else {
            showButtonFeedback(id, "Max (20) Reached", true);
        }
    } else {
        cart.push({ id, name, price: parseFloat(price), quantity: 1 });
        saveCart(cart);
        showButtonFeedback(id, "Added");
    }
}

// Provide UI feedback on the Add to Cart button
function showButtonFeedback(id, message, isWarning = false) {
    const button = document.querySelector(`button[data-item-id="${id}"]`);
    if (!button) return;

    const originalHTML = button.innerHTML;
    button.disabled = true;
    if (isWarning) {
        button.classList.replace("btn-add-cart", "btn-warning");
        button.textContent = message;
    } else {
        button.classList.replace("btn-add-cart", "btn-success");
        button.innerHTML = `<i class="bi bi-check-lg"></i> ${message}`;
    }

    setTimeout(() => {
        button.disabled = false;
        if (isWarning) {
            button.classList.replace("btn-warning", "btn-add-cart");
        } else {
            button.classList.replace("btn-success", "btn-add-cart");
        }
        button.innerHTML = originalHTML;
    }, 1500);
}

// Rerender the entire cart page UI
function renderCartPage() {
    const cartItemsContainer = document.getElementById("cart-items");
    const emptyCartContainer = document.getElementById("empty-cart");
    const cartSummaryContainer = document.getElementById("cart-summary");

    // Exit early if not on the cart page
    if (!cartItemsContainer) return;

    const cart = getCart();

    if (cart.length === 0) {
        // Toggle view containers
        if (emptyCartContainer) emptyCartContainer.classList.remove("d-none");
        if (cartSummaryContainer) cartSummaryContainer.classList.add("d-none");
        cartItemsContainer.innerHTML = "";
        return;
    }

    if (emptyCartContainer) emptyCartContainer.classList.add("d-none");
    if (cartSummaryContainer) cartSummaryContainer.classList.remove("d-none");

    cartItemsContainer.innerHTML = "";

    cart.forEach(item => {
        const itemRow = document.createElement("div");
        itemRow.className = "row align-items-center py-3 border-bottom cart-item-row";
        itemRow.dataset.itemId = item.id;

        // Item Name - Safe DOM assignment using textContent
        const nameCol = document.createElement("div");
        nameCol.className = "col-12 col-md-5 mb-2 mb-md-0";
        const nameText = document.createElement("h6");
        nameText.className = "fw-bold mb-0 text-dark";
        nameText.textContent = item.name;
        nameCol.appendChild(nameText);

        // Unit Price
        const priceCol = document.createElement("div");
        priceCol.className = "col-4 col-md-2";
        const priceText = document.createElement("span");
        priceText.className = "text-muted-sm";
        priceText.textContent = `₹${item.price.toFixed(2)}`;
        priceCol.appendChild(priceText);

        // Quantity Controls
        const qtyCol = document.createElement("div");
        qtyCol.className = "col-5 col-md-3 d-flex align-items-center gap-2";
        
        const decBtn = document.createElement("button");
        decBtn.type = "button";
        decBtn.className = "btn btn-outline-secondary btn-sm rounded-circle px-2 dec-qty-btn";
        decBtn.innerHTML = '<i class="bi bi-dash"></i>';
        decBtn.setAttribute("aria-label", "Decrease quantity");

        const qtySpan = document.createElement("span");
        qtySpan.className = "fw-bold px-2 qty-display text-dark";
        qtySpan.textContent = String(item.quantity);

        const incBtn = document.createElement("button");
        incBtn.type = "button";
        incBtn.className = "btn btn-outline-secondary btn-sm rounded-circle px-2 inc-qty-btn";
        incBtn.innerHTML = '<i class="bi bi-plus"></i>';
        incBtn.setAttribute("aria-label", "Increase quantity");

        qtyCol.appendChild(decBtn);
        qtyCol.appendChild(qtySpan);
        qtyCol.appendChild(incBtn);

        // Item Line Total and Remove
        const totalCol = document.createElement("div");
        totalCol.className = "col-3 col-md-2 text-end d-flex flex-column align-items-end";
        
        const lineTotalSpan = document.createElement("span");
        lineTotalSpan.className = "fw-bold text-dark mb-1";
        lineTotalSpan.textContent = `₹${(item.price * item.quantity).toFixed(2)}`;
        
        const removeBtn = document.createElement("button");
        removeBtn.type = "button";
        removeBtn.className = "btn btn-link text-danger text-decoration-none p-0 remove-item-btn small";
        removeBtn.textContent = "Remove";

        totalCol.appendChild(lineTotalSpan);
        totalCol.appendChild(removeBtn);

        // Assemble row
        itemRow.appendChild(nameCol);
        itemRow.appendChild(priceCol);
        itemRow.appendChild(qtyCol);
        itemRow.appendChild(totalCol);

        cartItemsContainer.appendChild(itemRow);
    });

    // Update Totals Summary
    calculateTotals(cart);
}

// Calculate subtotal, tax, and total
function calculateTotals(cart) {
    const subtotalElement = document.getElementById("cart-subtotal");
    const taxElement = document.getElementById("cart-tax");
    const totalElement = document.getElementById("cart-total");

    const subtotal = cart.reduce((sum, item) => sum + (item.price * item.quantity), 0);
    const tax = subtotal * TAX_RATE;
    const grandTotal = subtotal + tax;

    if (subtotalElement) subtotalElement.textContent = `₹${subtotal.toFixed(2)}`;
    if (taxElement) taxElement.textContent = `₹${tax.toFixed(2)}`;
    if (totalElement) totalElement.textContent = `₹${grandTotal.toFixed(2)}`;
}

// Attach Event Listeners on DOM load
document.addEventListener("DOMContentLoaded", () => {
    // 1. Check for success marker and clear localStorage first
    const successMarker = document.getElementById("checkout-success-marker");
    if (successMarker && successMarker.dataset.clearCartOnLoad === "true") {
        localStorage.removeItem(CART_STORAGE_KEY);
    }

    // 2. Load initial cart states and run backend synchronization
    const cart = getCart();
    updateCartCount(cart);
    synchronizeCartWithServer();

    // 2. Setup Add to Cart click listeners (Menu Page)
    const menuGrid = document.querySelector(".row-cols-1"); // main catalog grid
    if (menuGrid) {
        menuGrid.addEventListener("click", (e) => {
            const button = e.target.closest(".btn-add-cart");
            if (button) {
                const id = button.dataset.itemId;
                const name = button.dataset.itemName;
                const price = button.dataset.itemPrice;
                if (id && name && price) {
                    addItemToCart(id, name, price);
                }
            }
        });
    }

    // 3. Setup Cart Page Dynamic Control Listeners (Event Delegation)
    const cartItemsContainer = document.getElementById("cart-items");
    if (cartItemsContainer) {
        renderCartPage();

        cartItemsContainer.addEventListener("click", (e) => {
            const row = e.target.closest(".cart-item-row");
            if (!row) return;

            const itemId = row.dataset.itemId;
            const currentCart = getCart();
            const item = currentCart.find(i => i.id === itemId);
            if (!item) return;

            // Handle quantity decrease
            if (e.target.closest(".dec-qty-btn")) {
                if (item.quantity > 1) {
                    item.quantity -= 1;
                    saveCart(currentCart);
                    renderCartPage();
                } else {
                    // Decreasing from 1 removes the item from the cart
                    const updatedCart = currentCart.filter(i => i.id !== itemId);
                    saveCart(updatedCart);
                    renderCartPage();
                }
            }

            // Handle quantity increase
            if (e.target.closest(".inc-qty-btn")) {
                if (item.quantity < MAX_QUANTITY) {
                    item.quantity += 1;
                    saveCart(currentCart);
                    renderCartPage();
                }
            }

            // Handle item removal
            if (e.target.closest(".remove-item-btn")) {
                const updatedCart = currentCart.filter(i => i.id !== itemId);
                saveCart(updatedCart);
                renderCartPage();
            }
        });
    }

    // 4. Setup Clear Cart functionality
    const clearCartBtn = document.getElementById("clear-cart-btn");
    const confirmClearBtn = document.getElementById("confirm-clear-cart-btn");
    
    if (clearCartBtn) {
        clearCartBtn.addEventListener("click", () => {
            // Check if Bootstrap modal is available
            if (typeof bootstrap !== 'undefined') {
                const modalElement = document.getElementById('clearCartModal');
                if (modalElement) {
                    const modal = new bootstrap.Modal(modalElement);
                    modal.show();
                }
            } else {
                // Fallback if bootstrap is somehow not loaded
                if (confirm("Are you sure you want to clear your entire cart?")) {
                    executeClearCart();
                }
            }
        });
    }

    if (confirmClearBtn) {
        confirmClearBtn.addEventListener("click", () => {
            executeClearCart();
            // Hide modal
            const modalElement = document.getElementById('clearCartModal');
            if (modalElement && typeof bootstrap !== 'undefined') {
                const modal = bootstrap.Modal.getInstance(modalElement);
                if (modal) modal.hide();
            }
        });
    }

    function executeClearCart() {
        localStorage.removeItem(CART_STORAGE_KEY);
        updateCartCount([]);
        renderCartPage();
        synchronizeCartWithServer();
    }
});
