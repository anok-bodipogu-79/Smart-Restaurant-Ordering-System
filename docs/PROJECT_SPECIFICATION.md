# MASTER PROJECT SPECIFICATION PROMPT

## Smart Restaurant Food Ordering & Kitchen Dashboard

You are an expert senior full-stack developer specializing in Python, Django, PostgreSQL, JavaScript, Bootstrap 5, secure web application development, automated testing, Git, GitHub, and Render deployment.

Your task is to help me build a complete capstone project named:

**Smart Restaurant Food Ordering & Kitchen Dashboard**

You must implement this project carefully, incrementally, and phase by phase.

Do not generate or implement the entire application at once.

Before making changes in each phase:

1. Inspect the existing project structure.
2. Inspect all relevant existing files.
3. Understand the current implementation.
4. Identify what is already working.
5. Determine exactly which files need modification.
6. Preserve all existing working functionality.
7. Make only changes required for the current phase.
8. Run appropriate validation and tests after implementation.
9. Fix errors before considering the phase complete.
10. Provide a concise summary of completed work.

Do not proceed to the next implementation phase unless I explicitly request it.

---

# 1. PROJECT OVERVIEW

Build a full-stack restaurant ordering and kitchen order management web application.

The application must allow customers to:

* browse restaurant menu items
* view menu items grouped by categories
* filter food items by category
* view food images
* view food descriptions
* view food prices
* identify vegetarian and non-vegetarian items
* identify spicy items if supported by the model
* view item availability
* add available food items to a shopping cart
* increase item quantities
* decrease item quantities
* remove items
* view cart count
* view subtotal
* view tax
* view grand total
* retain cart data after browser refresh
* proceed to checkout
* enter customer information
* place an order
* receive a unique Order ID
* track order progress using the Order ID

The application must allow authenticated kitchen staff to:

* log in securely
* access the kitchen dashboard
* view active orders
* view ordered food items and quantities
* view customer and table information
* view order creation time
* update valid order statuses
* process orders from Received to Preparing
* process orders from Preparing to Ready
* process orders from Ready to Completed

The Django administrator must be able to:

* manage categories
* manage menu items
* manage menu availability
* manage orders
* manage order items
* manage staff users

---

# 2. CORE PROJECT WORKFLOW

The main application workflow must be:

Customer Opens Website

↓

Views Restaurant Menu

↓

Filters Menu by Category

↓

Adds Available Items to Cart

↓

JavaScript Updates Cart

↓

Cart Stored in localStorage

↓

Cart Synchronized with Django Session

↓

Customer Opens Checkout

↓

Customer Enters Information

↓

Django Validates Customer and Cart Data

↓

Django Retrieves Current Menu Prices from Database

↓

Django Calculates Final Amount

↓

Order and OrderItems Are Created Atomically

↓

Customer Receives Unique Order ID

↓

Order Appears on Kitchen Dashboard

↓

Kitchen Staff Updates Order Status

↓

Customer Tracking Page Polls Current Status

↓

Order Becomes Completed

---

# 3. FIXED TECHNOLOGY STACK

Use the following technology stack.

## Backend

* Python 3.11 or compatible stable version
* Django
* Django ORM
* Django MVT architecture

## Frontend

* HTML5
* CSS3
* Vanilla JavaScript
* Bootstrap 5
* Bootstrap Icons

## Database

Development:

* SQLite is allowed for local development

Production:

* PostgreSQL

## Cart Storage

* Browser localStorage
* Django sessions

## Live Status Updates

Use JavaScript polling.

Do not use:

* WebSockets
* Django Channels
* Redis
* Celery

unless explicitly requested later.

## Production

* Gunicorn
* WhiteNoise
* PostgreSQL
* Render

## Version Control

* Git
* GitHub

---

# 4. TECHNOLOGIES THAT MUST NOT BE INTRODUCED

Do not introduce the following unless explicitly requested:

* React
* Angular
* Vue
* Next.js
* Node.js backend
* Express.js
* Django REST Framework
* Docker
* Kubernetes
* Redis
* Celery
* WebSockets
* Django Channels
* external payment gateways
* unnecessary JavaScript frameworks
* unnecessary Python packages

Keep the project simple, maintainable, secure, and suitable for a Django full-stack capstone project.

---

# 5. PROJECT NAMING

Use:

Django project name:

restaurant_project

Django application name:

restaurant

Root folder:

smart-restaurant-ordering-system

Do not change these names after project creation unless explicitly requested.

---

# 6. REQUIRED PROJECT STRUCTURE

The target project structure should be:

smart-restaurant-ordering-system/

```
manage.py

requirements.txt

.gitignore

.env.example

README.md

render.yaml

create_superuser.py

restaurant_project/

    __init__.py

    settings.py

    urls.py

    wsgi.py

    asgi.py

restaurant/

    __init__.py

    admin.py

    apps.py

    forms.py

    models.py

    urls.py

    views.py

    tests.py

    migrations/

    management/

        __init__.py

        commands/

            __init__.py

            seed_menu.py

    templates/

        restaurant/

            base.html

            menu.html

            cart.html

            checkout.html

            order_success.html

            order_tracking.html

            kitchen_login.html

            kitchen_dashboard.html

    static/

        restaurant/

            css/

                style.css

            js/

                cart.js

                tracking.js

                kitchen.js
```

If additional files are genuinely required, explain why before adding them.

Do not create unnecessary files or folders.

---

# 7. DATABASE DESIGN

Implement the following core models.

## Category Model

Fields:

* name
* icon

Requirements:

* name must be clear and human-readable
* implement **str**
* use correct plural naming in Django Admin
* categories should have predictable ordering

Example categories:

* Appetizers
* Main Course
* Desserts
* Beverages

---

## MenuItem Model

Fields:

* category
* name
* description
* price
* is_vegetarian
* is_spicy
* is_available
* image_url

Requirements:

* category must use ForeignKey
* use related_name="items"
* price must use DecimalField
* price must never use float
* implement **str**
* menu items should have predictable ordering
* unavailable items must not be orderable

---

## Order Model

Fields:

* customer_name
* customer_phone
* table_number
* total_amount
* status
* created_at

Required statuses:

RECEIVED

PREPARING

READY

COMPLETED

Display names:

* Order Received
* In Kitchen - Preparing
* Ready for Pickup / Delivery
* Completed

Requirements:

* default status must be RECEIVED
* total_amount must use DecimalField
* created_at must use auto_now_add
* implement **str**
* newest orders should be easily retrievable

---

## OrderItem Model

Fields:

* order
* menu_item
* quantity
* price_at_order

Requirements:

* order must use ForeignKey
* use related_name="items"
* menu_item must use ForeignKey
* quantity must be positive
* price_at_order must use DecimalField
* implement **str**

The purpose of price_at_order is to preserve the menu item price at the time the order was created.

Changing the current MenuItem price must never modify historical order prices.

---

# 8. DATABASE RELATIONSHIPS

Required relationships:

Category

One-to-Many

MenuItem

Order

One-to-Many

OrderItem

MenuItem

One-to-Many

OrderItem

The relationship structure must effectively represent:

Category → MenuItem

Order → OrderItem ← MenuItem

Use proper Django ForeignKey relationships and related_name values.

---

# 9. REQUIRED PAGES

Implement the following pages.

## Base Template

File:

base.html

Responsibilities:

* Bootstrap 5 integration
* Bootstrap Icons integration
* common navigation
* cart count indicator
* messages display
* reusable page structure
* responsive layout
* common footer

---

## Menu Page

File:

menu.html

Responsibilities:

* display categories
* display menu items
* responsive Bootstrap cards
* food image
* name
* description
* price
* vegetarian/non-vegetarian badge
* spicy badge where applicable
* availability information
* Add to Cart button
* category filtering

Unavailable items must not be addable to the cart.

---

## Cart Page

File:

cart.html

Responsibilities:

* display cart items
* display quantities
* increase quantity
* decrease quantity
* remove item
* display subtotal
* display tax
* display grand total
* empty cart state
* checkout button

---

## Checkout Page

File:

checkout.html

Responsibilities:

* customer name
* customer phone
* optional table number
* order summary
* subtotal
* tax
* final total
* secure POST form
* CSRF protection
* validation errors
* Place Order button

---

## Order Success Page

File:

order_success.html

Responsibilities:

* success message
* unique Order ID
* order summary
* final total
* tracking link
* return-to-menu option

---

## Order Tracking Page

File:

order_tracking.html

Responsibilities:

* accept or display Order ID
* show current order status
* visual order progress
* Received
* Preparing
* Ready
* Completed
* automatically update status using JavaScript polling

---

## Kitchen Login Page

File:

kitchen_login.html

Responsibilities:

* secure staff authentication
* username
* password
* CSRF protection
* validation errors

---

## Kitchen Dashboard

File:

kitchen_dashboard.html

Responsibilities:

* authenticated access only
* display active orders
* display Order ID
* customer information
* table number
* order items
* quantities
* order creation time
* total amount
* current status
* valid next-status button

Completed orders may be separated from active orders or excluded from the default active dashboard.

---

# 10. URL DESIGN

Use clear and maintainable URL routes.

Recommended routes:

/                      → Menu page

/cart/                 → Cart page

/cart/sync/            → Synchronize localStorage cart with Django session

/checkout/             → Checkout

/order/success/<id>/   → Order success page

/order/track/           → Order tracking form

/order/<id>/            → Specific order tracking page

/order/<id>/status/     → Order status polling endpoint

/kitchen/login/         → Kitchen login

/kitchen/logout/        → Kitchen logout

/kitchen/               → Kitchen dashboard

/kitchen/order/<id>/status/ → Update order status

Use named URLs and Django namespaces.

Avoid hardcoded URLs inside templates and views.

---

# 11. SHOPPING CART ARCHITECTURE

The shopping cart is a critical component.

The frontend cart must use:

* JavaScript
* localStorage

The backend cart must use:

* Django sessions

The browser cart should store only necessary data.

Recommended cart data:

* menu item ID
* quantity

Do not trust browser-provided:

* item names
* prices
* subtotal
* tax
* total amount
* availability

The backend must retrieve trusted information from the database.

---

# 12. CART BEHAVIOR

Required cart functionality:

* Add to Cart
* increase quantity
* decrease quantity
* remove item
* clear cart
* persistent cart after refresh
* cart item count
* subtotal display
* tax display
* grand total display
* synchronize cart with Django session
* prevent invalid quantities
* prevent ordering unavailable menu items

The JavaScript cart is for frontend convenience.

Django remains the authority for:

* menu item existence
* availability
* prices
* quantities
* subtotal
* tax
* grand total

---

# 13. TAX CALCULATION

Use one centralized tax rate.

Do not duplicate arbitrary tax percentages across multiple files.

Define a clear tax rate configuration.

Recommended initial tax:

5%

Use Decimal for backend financial calculations.

The backend calculation should follow:

Subtotal = Sum of Current Menu Item Price × Quantity

Tax = Subtotal × Tax Rate

Grand Total = Subtotal + Tax

Use proper Decimal rounding where necessary.

The frontend may display estimated calculations.

The backend calculation is always authoritative.

---

# 14. CHECKOUT REQUIREMENTS

The checkout process must:

1. accept a POST request
2. validate CSRF
3. validate customer information
4. retrieve cart from Django session
5. reject empty carts
6. validate menu item IDs
7. retrieve MenuItems from the database
8. verify item availability
9. validate quantities
10. retrieve current prices
11. calculate subtotal
12. calculate tax
13. calculate final total
14. create Order
15. create OrderItems
16. store price_at_order
17. perform database operations atomically
18. clear the Django session cart after successful order creation
19. return the unique Order ID
20. redirect to the order success page

Use transaction.atomic() or an equivalent safe Django transaction mechanism.

If order creation fails, partial Order or OrderItem records must not remain in the database.

---

# 15. CUSTOMER VALIDATION RULES

## Customer Name

* required
* strip unnecessary whitespace
* reasonable minimum and maximum length
* reject invalid empty input

## Customer Phone

* required
* validate using an appropriate format
* allow realistic Indian phone number input
* store safely

## Table Number

* optional
* must be a positive integer when supplied

## Cart

* must not be empty
* menu item IDs must exist
* quantities must be positive integers
* quantities must have a reasonable maximum limit
* unavailable items must not be ordered

Recommended maximum quantity per item:

20

---

# 16. ORDER STATUS RULES

Valid status workflow:

RECEIVED

↓

PREPARING

↓

READY

↓

COMPLETED

Only allow forward status transitions.

Allowed:

RECEIVED → PREPARING

PREPARING → READY

READY → COMPLETED

Do not allow:

RECEIVED → READY

RECEIVED → COMPLETED

PREPARING → COMPLETED

COMPLETED → READY

or any arbitrary backward transition.

Validate status transitions on the backend.

Never rely only on frontend buttons for status security.

---

# 17. LIVE ORDER TRACKING

Implement near-real-time tracking using JavaScript polling.

Recommended polling interval:

5 seconds

The tracking JavaScript should:

1. request the current order status endpoint
2. receive the current status
3. update the visual progress indicator
4. stop unnecessary polling when the order reaches COMPLETED
5. handle temporary request failures gracefully

Do not implement WebSockets.

Do not implement Django Channels.

Do not reload the complete page every 5 seconds.

Only retrieve the required status data.

---

# 18. KITCHEN AUTHENTICATION AND AUTHORIZATION

The kitchen dashboard must not be publicly accessible.

Requirements:

* use Django authentication
* kitchen login required
* kitchen dashboard protected
* order status update protected
* anonymous users cannot access kitchen functionality
* anonymous users cannot update order status
* use POST requests for state-changing operations
* use CSRF protection
* validate order transitions on the backend

Prefer staff-only access.

A normal anonymous customer must never be able to change an order status.

---

# 19. DJANGO ADMIN REQUIREMENTS

Register:

* Category
* MenuItem
* Order
* OrderItem

Improve admin usability where appropriate using:

* list_display
* list_filter
* search_fields
* ordering

Do not over-engineer the Django Admin interface.

---

# 20. SAMPLE DATA

Create a custom Django management command:

seed_menu

File:

restaurant/management/commands/seed_menu.py

The command should create realistic sample data.

Categories:

* Appetizers
* Main Course
* Desserts
* Beverages

Create multiple realistic menu items for every category.

Use Indian restaurant-style menu items.

Examples may include:

* Paneer Tikka
* Chicken 65
* Vegetable Spring Rolls
* Chicken Biryani
* Paneer Butter Masala
* Vegetable Fried Rice
* Gulab Jamun
* Brownie
* Ice Cream
* Masala Soda
* Fresh Lime Juice
* Cold Coffee

The command should be idempotent where practical.

Running it multiple times should not unnecessarily duplicate data.

---

# 21. FRONTEND DESIGN REQUIREMENTS

Use:

* Bootstrap 5
* Bootstrap Icons
* custom CSS
* responsive layouts

The UI should be:

* modern
* clean
* restaurant-themed
* responsive
* easy to navigate
* suitable for desktop
* suitable for tablet
* suitable for mobile

Avoid:

* excessive animations
* unnecessary dependencies
* complicated UI frameworks
* huge JavaScript files
* inline CSS where maintainable external CSS is better
* duplicated HTML structures

Use Django template inheritance.

---

# 22. ERROR AND EMPTY STATES

Implement clear handling for:

* no menu items
* unavailable menu items
* empty cart
* invalid checkout data
* missing order
* invalid Order ID
* unauthorized kitchen access
* invalid status transition
* failed cart synchronization
* temporary polling failure
* database errors where appropriate

Do not expose sensitive exception details to end users.

---

# 23. SECURITY REQUIREMENTS

The project must follow these rules.

## CSRF

Use Django CSRF protection.

All state-changing requests must be protected.

## HTTP Methods

Use POST for:

* checkout
* status changes
* cart synchronization where appropriate
* login/logout according to secure Django patterns

Do not use GET requests to modify database state.

## Backend Validation

Validate:

* menu item existence
* availability
* quantities
* customer information
* order existence
* valid status transitions

## Financial Security

Never trust browser-provided prices.

Never trust browser-provided totals.

Never trust browser-provided tax calculations.

Always calculate final financial values on the Django backend.

## Authentication

Protect kitchen functionality.

## Environment Variables

Do not hardcode production secrets.

## Production Settings

Use:

DEBUG=False

Use secure SECRET_KEY configuration.

Configure ALLOWED_HOSTS correctly.

Configure CSRF_TRUSTED_ORIGINS correctly.

Do not use wildcard production configuration unless genuinely necessary.

---

# 24. ENVIRONMENT VARIABLES

Support appropriate environment variables.

Expected variables:

SECRET_KEY

DEBUG

DATABASE_URL

ADMIN_USERNAME

ADMIN_EMAIL

ADMIN_PASSWORD

Do not commit real environment values.

Create:

.env.example

The .env.example file may contain safe placeholder values only.

Do not commit:

.env

---

# 25. GITIGNORE REQUIREMENTS

Create an appropriate .gitignore.

Exclude at minimum:

* venv/
* .venv/
* **pycache**/
* *.pyc
* .env
* IDE-specific files where appropriate
* operating system temporary files
* generated static files where appropriate
* local development artifacts

Handle db.sqlite3 according to the final project development strategy.

Do not accidentally commit secrets.

---

# 26. TESTING REQUIREMENTS

Testing is mandatory.

Use Django's built-in testing framework unless there is a strong reason otherwise.

Test the following areas.

## Model Tests

Test:

* Category creation
* MenuItem creation
* Order creation
* OrderItem creation
* string representations
* model relationships
* default order status

## Menu Tests

Test:

* menu page loads
* categories display
* available items display
* unavailable item behavior

## Cart and Checkout Tests

Test:

* empty cart rejection
* valid checkout
* invalid quantities
* nonexistent menu items
* unavailable menu items
* backend price calculation
* browser price manipulation cannot affect final total
* correct Order creation
* correct OrderItem creation
* correct price_at_order
* session cart clearing
* transaction safety where practical

## Order Tracking Tests

Test:

* valid order tracking
* nonexistent Order ID
* status endpoint response
* completed order response

## Kitchen Tests

Test:

* anonymous dashboard access rejected
* authenticated staff access allowed
* anonymous status update rejected
* valid status transition
* invalid status transition
* backward transition rejected
* POST-only status changes

Run:

python manage.py check

and:

python manage.py test

after relevant implementation phases.

All tests must pass before the project is considered complete.

---

# 27. DEPLOYMENT REQUIREMENTS

Prepare the application for Render deployment.

Use:

* Gunicorn
* WhiteNoise
* PostgreSQL

Create:

requirements.txt

render.yaml

create_superuser.py

Production configuration must support environment variables.

The deployment process should handle:

* dependency installation
* collectstatic
* migrations
* application startup

Do not use production SQLite as persistent storage.

Use PostgreSQL.

---

# 28. STATIC FILE CONFIGURATION

Use WhiteNoise.

Configure:

STATIC_URL

STATIC_ROOT

WhiteNoise middleware

appropriate static file storage configuration compatible with the installed Django version

Do not blindly use deprecated Django settings.

Check compatibility with the actual Django version installed.

---

# 29. SUPERUSER CREATION

If automatic superuser creation is implemented:

* use environment variables
* do not expose the password in logs
* do not hardcode production credentials
* safely handle existing users
* safely handle database errors

Expected variables:

ADMIN_USERNAME

ADMIN_EMAIL

ADMIN_PASSWORD

Never print the admin password.

---

# 30. RENDER CONFIGURATION

The Render configuration should:

* use the correct Python runtime
* install requirements
* run collectstatic
* run migrations appropriately
* start Gunicorn
* configure required environment variables
* use PostgreSQL
* avoid unnecessary memory consumption

Do not blindly duplicate migration commands in multiple deployment lifecycle stages.

Explain the chosen deployment configuration before finalizing it.

---

# 31. README REQUIREMENTS

Create a complete README.md containing:

* project title
* project overview
* problem statement
* features
* user roles
* technology stack
* architecture overview
* database models
* installation instructions
* virtual environment setup
* dependency installation
* migrations
* sample data creation
* development server instructions
* testing instructions
* environment variables
* production deployment overview
* project folder structure
* future enhancements

Keep the README accurate.

Do not document features that are not actually implemented.

---

# 32. CODE QUALITY RULES

Follow these rules throughout development.

* follow Django conventions
* use meaningful variable names
* use meaningful function names
* avoid unnecessary code duplication
* avoid giant view functions
* avoid business logic inside templates
* avoid unnecessary dependencies
* use Decimal for financial values
* use database transactions for checkout
* use named URLs
* use Django template inheritance
* keep JavaScript maintainable
* keep CSS maintainable
* use comments only where they add useful context
* remove dead code
* remove unused imports
* handle exceptions appropriately
* do not suppress errors without a reason
* do not use placeholder implementations in completed phases

---

# 33. CRITICAL AI AGENT BEHAVIOR RULES

These instructions are mandatory.

## Rule 1: Inspect Before Editing

Before modifying any existing file:

* inspect the file
* understand the existing implementation
* identify dependencies
* preserve working functionality

Never overwrite files blindly.

---

## Rule 2: Work Phase by Phase

Do not implement the entire project in one response or one operation.

Complete only the phase I explicitly request.

Stop after completing and validating that phase.

---

## Rule 3: Do Not Modify Unrelated Code

If a file or feature is already working and unrelated to the current task:

DO NOT MODIFY IT.

Avoid unnecessary refactoring.

Avoid formatting entire files unless required.

Avoid renaming working files, functions, classes, URLs, or variables without a clear technical reason.

---

## Rule 4: Make Minimal Changes

Use the smallest safe change necessary to complete the current requirement.

Do not rewrite entire files when a targeted modification is sufficient.

---

## Rule 5: Never Delete Working Functionality Without Permission

Do not remove:

* existing models
* existing views
* existing templates
* existing URLs
* existing tests
* existing configuration
* existing dependencies

unless removal is technically required.

If removal is required, explain why before making the change.

---

## Rule 6: Do Not Change the Technology Stack

Do not introduce new frameworks, databases, services, or architecture patterns without explicit permission.

---

## Rule 7: Validate Every Phase

After implementation, run relevant commands.

Examples:

python manage.py check

python manage.py makemigrations --check

python manage.py test

Run additional appropriate validation where necessary.

Do not claim success if validation fails.

---

## Rule 8: Fix Errors Before Stopping

If the current phase introduces errors:

* investigate them
* identify the root cause
* fix them
* rerun validation

Do not leave the project knowingly broken.

---

## Rule 9: Never Hide Failures

If a command fails:

* report the failure
* explain the cause
* fix it when possible
* rerun the command

Do not claim that tests passed when they did not.

---

## Rule 10: Protect Secrets

Never:

* commit .env
* hardcode passwords
* expose SECRET_KEY
* print production passwords
* commit database credentials

---

## Rule 11: Backend Is Authoritative

Never trust the browser for:

* prices
* totals
* tax
* availability
* valid order statuses

Validate all important data on the Django backend.

---

## Rule 12: Preserve Database History

Historical order prices must remain accurate.

Always use price_at_order.

Never calculate historical order totals using current MenuItem prices.

---

## Rule 13: Avoid Over-Engineering

This is a capstone Django project.

Prefer simple, secure, maintainable solutions.

Do not add complex infrastructure unless explicitly requested.

---

## Rule 14: Ask Only When Truly Blocked

Do not repeatedly ask unnecessary questions.

If a reasonable implementation decision is already defined in this specification, follow it.

Ask for clarification only when proceeding would create a meaningful architectural conflict or risk damaging existing work.

---

## Rule 15: Do Not Automatically Proceed

After completing a phase:

STOP.

Provide the phase summary.

Wait for my next instruction.

---

# 34. REQUIRED PHASE-BY-PHASE IMPLEMENTATION PLAN

Implement the project using the following phases.

## PHASE 1: Environment and Django Project Setup

Tasks:

* inspect current directory
* create virtual environment if needed
* install Django and initial dependencies
* create Django project
* create restaurant app
* configure installed apps
* create initial folder structure
* create .gitignore
* create .env.example
* create initial requirements.txt
* run Django system check
* run initial migrations
* verify development server configuration

Stop after Phase 1.

---

## PHASE 2: Database Models

Tasks:

* implement Category
* implement MenuItem
* implement Order
* implement OrderItem
* add validation where appropriate
* create migrations
* run migrations
* test models
* run Django checks

Stop after Phase 2.

---

## PHASE 3: Django Admin and Sample Data

Tasks:

* register models
* improve admin usability
* create seed_menu management command
* create realistic categories
* create realistic menu items
* make seeding idempotent
* verify sample data

Stop after Phase 3.

---

## PHASE 4: Base Frontend and Menu System

Tasks:

* configure templates
* configure static files
* create base template
* create navigation
* create MenuListView
* create menu URL
* create responsive menu page
* implement category filtering
* implement dietary badges
* implement availability behavior
* test menu views

Stop after Phase 4.

---

## PHASE 5: JavaScript Shopping Cart

Tasks:

* create cart.js
* implement localStorage cart
* Add to Cart
* increase quantity
* decrease quantity
* remove item
* clear cart
* cart count
* estimated calculations
* cart page
* empty cart state
* responsive cart interface
* validate frontend behavior

Stop after Phase 5.

---

## PHASE 6: Django Session Cart Synchronization

Tasks:

* create cart synchronization endpoint
* accept only necessary cart data
* validate menu item IDs
* validate quantities
* verify availability
* retrieve trusted prices
* store validated cart in Django session
* implement CSRF protection
* handle synchronization errors
* test synchronization

Stop after Phase 6.

---

## PHASE 7: Checkout and Order Creation

Tasks:

* create checkout form
* create checkout page
* validate customer data
* validate session cart
* calculate trusted totals
* implement tax calculation
* use Decimal
* use transaction.atomic
* create Order
* create OrderItems
* store price_at_order
* clear cart after success
* create success page
* display Order ID
* test checkout thoroughly

Stop after Phase 7.

---

## PHASE 8: Kitchen Authentication

Tasks:

* create kitchen login
* create kitchen logout
* require authentication
* require appropriate staff access
* protect kitchen URLs
* test unauthorized access
* test authorized access

Stop after Phase 8.

---

## PHASE 9: Kitchen Dashboard

Tasks:

* create KitchenDashboardView
* display active orders
* display customer information
* display items and quantities
* display total
* display current status
* implement valid next-status updates
* enforce POST
* enforce CSRF
* validate backend status transitions
* test dashboard behavior

Stop after Phase 9.

---

## PHASE 10: Customer Order Tracking

Tasks:

* create tracking form
* create tracking page
* create status endpoint
* create tracking.js
* implement 5-second polling
* update visual progress
* stop polling when completed
* handle invalid Order IDs
* handle request errors
* test tracking

Stop after Phase 10.

---

## PHASE 11: Complete Testing and Security Review

Tasks:

* review all tests
* add missing model tests
* add missing view tests
* add checkout security tests
* add price manipulation tests
* add unavailable item tests
* add authorization tests
* add status transition tests
* run complete test suite
* run Django system check
* inspect for security problems
* fix all identified problems

Stop after Phase 11.

---

## PHASE 12: Production and PostgreSQL Configuration

Tasks:

* configure environment variables
* configure PostgreSQL
* configure DATABASE_URL
* configure WhiteNoise
* configure static files
* configure Gunicorn
* configure production settings
* create safe create_superuser.py
* update requirements.txt
* verify DEBUG behavior
* verify ALLOWED_HOSTS
* verify CSRF_TRUSTED_ORIGINS

Stop after Phase 12.

---

## PHASE 13: Render Deployment Configuration

Tasks:

* create render.yaml
* review build command
* review start command
* configure PostgreSQL
* configure environment variables
* verify migration strategy
* verify collectstatic
* verify Gunicorn startup
* check memory-conscious configuration

Stop after Phase 13.

---

## PHASE 14: Documentation and Final Cleanup

Tasks:

* create complete README
* document setup
* document migrations
* document seed command
* document tests
* document deployment
* verify folder structure
* remove dead code
* remove unused imports
* verify .gitignore
* verify no secrets are committed
* run final tests
* run final Django check

Stop after Phase 14.

---

# 35. REQUIRED RESPONSE FORMAT AFTER EACH PHASE

After completing a phase, respond using this structure:

## Phase Completed

State the phase number and name.

## Work Completed

Briefly list the work performed.

## Files Created

List newly created files.

## Files Modified

List modified files.

## Validation Performed

List commands executed.

Example:

python manage.py check

python manage.py test

## Validation Results

Report the actual results.

Do not claim tests passed unless they actually passed.

## Issues Found and Fixed

Explain any problems encountered and how they were resolved.

If there were no issues, state that clearly.

## Current Project Status

Briefly explain what functionality is now working.

## Next Phase

State only the next phase name.

Do not begin implementing it.

---

# 36. DEFINITION OF PROJECT COMPLETION

The project is complete only when:

* customers can browse menu items
* categories can be filtered
* unavailable items cannot be ordered
* customers can manage a persistent shopping cart
* localStorage cart works
* Django session cart works
* checkout validates all important data
* backend calculates trusted prices
* orders are created atomically
* OrderItems preserve price_at_order
* customers receive an Order ID
* authenticated kitchen staff can view orders
* anonymous users cannot access protected kitchen functionality
* kitchen staff can perform only valid status transitions
* customers can track orders
* polling updates status
* all required tests pass
* Django system checks pass
* PostgreSQL production configuration works
* static files work in production
* secrets are stored securely
* the application is prepared for Render deployment
* README documentation matches actual functionality

---

