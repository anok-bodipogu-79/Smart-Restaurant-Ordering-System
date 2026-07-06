# Smart Restaurant Food Ordering & Kitchen Dashboard

Welcome to the **Smart Restaurant Food Ordering & Kitchen Dashboard** capstone project. This is a complete, production-ready Django full-stack web application designed for interactive restaurant menu browsing, real-time customer order tracking, and a kitchen management console for restaurant staff.

---

## Implemented Features

### Customer Features
- **Responsive Food Menu**: Filter items by categories (e.g. Appetizers, Mains, Drinks) with dietary tags (Veg/Non-Veg) and item availability status.
- **Interactive Shopping Cart**: Client-side Vanilla JS shopping cart backed by browser `localStorage` persisting items, capping quantities, and displaying estimated costs.
- **Django Session Synchronization**: Automatic server synchronization layer validating quantities (1-20 limits), active status, and database-authoritative menu prices.
- **Secure Checkout Page**: Customer details form with whitespace trimming, name validation (min 2 chars), and normalized 10-digit Indian phone numbers (+91 prefix).
- **Order Success Page**: Direct confirmation displaying summary details, order metrics, and a clearing script to prevent duplicate orders or race states.
- **Live Order Tracking**: Customer-facing live tracking page displaying visual timeline stages with a 5-second recursive polling fetch mechanism.

### Kitchen Staff Features
- **Dedicated Kitchen Login**: Custom staff-protected login layout supporting secure authentication and redirects.
- **Staff Authorization (403)**: Non-staff users trying to access staff consoles are blocked with HTTP 403 Forbidden screens.
- **Kitchen Dashboard**: Visual three-column workflow dashboard (Received, Preparing, Ready) listing active orders sorted oldest first (chronological priority).
- **Sequential Status Transitions**: Status updates advance sequentially on POST forms: `RECEIVED → PREPARING → READY → COMPLETED`.
- **Database Row Lock Protection**: State-changing status endpoints wrap operations inside `transaction.atomic()` using `select_for_update()` to prevent concurrent update races.

---

## Tech Stack

- **Backend**: Python 3.11/3.13, Django 6.0.6, Django ORM
- **Frontend**: HTML5, CSS3, Vanilla JavaScript, Bootstrap 5, Bootstrap Icons
- **Database**: SQLite (Local development), PostgreSQL (Production)
- **Production Server**: Gunicorn, WhiteNoise, Render Web Service

---

## Folder Structure

```text
Smart-Restaurant-Ordering-System/
├── create_superuser.py         # Idempotent superuser creation script
├── manage.py                   # Django management entry point
├── render.yaml                 # Render Blueprint configuration
├── requirements.txt            # Python production dependencies
├── .env.example                # Local environment placeholders
├── .gitignore                  # Git untracked directories checklist
├── README.md                   # Complete project documentation
├── restaurant_project/         # Django project settings layer
│   ├── settings.py             # Project configurations (WhiteNoise, database fallback)
│   ├── urls.py                 # Root URL paths registry
│   └── wsgi.py                 # WSGI entry point
└── restaurant/                 # Django restaurant application
    ├── admin.py                # Admin panel configuration
    ├── forms.py                # Validation forms (Checkout, Tracking)
    ├── models.py               # DB Schema (Category, MenuItem, Order, OrderItem)
    ├── tests.py                # Complete integration & unit tests
    ├── urls.py                 # Application routes mapping
    ├── views.py                # Main request logic & class-based views
    ├── static/                 # CSS styling assets & JS modules
    │   └── restaurant/
    │       ├── css/style.css
    │       └── js/
    │           ├── cart.js     # Shopping cart and synchronization logic
    │           └── order_tracking.js # Live polling client script
    └── templates/              # HTML layout templates
```

---

## Local Setup Instructions (Windows PowerShell)

Follow these steps to run the project locally on your machine:

### 1. Clone & Enter Project Directory
```powershell
cd "Smart-Restaurant-Ordering-System"
```

### 2. Create and Activate Virtual Environment
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 3. Install Python Dependencies
```powershell
pip install -r requirements.txt
```

### 4. Create and Configure Environment Variables
Create a file named `.env` in the project root directory. Copy the contents of `.env.example` into it and fill in your local configurations:
```text
SECRET_KEY=local-dev-secret-key-123
DEBUG=True
DATABASE_URL=
ALLOWED_HOSTS=localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=

ADMIN_USERNAME=admin
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=adminpassword123

WEB_CONCURRENCY=2
```

### 5. Apply Database Migrations
```powershell
python manage.py migrate
```

### 6. Populate Menu Seeding Data
```powershell
python manage.py seed_menu
```

### 7. Create Superuser (Admin Account)
```powershell
python create_superuser.py
```

### 8. Start Local Development Server
```powershell
python manage.py runserver
```
Open your browser and navigate to `http://127.0.0.1:8000/`.

---

## Production Deployment on Render

To deploy the application to Render:

### 1. Create a PostgreSQL Database
- Create a PostgreSQL database instance on Render (or an external provider such as Neon).
- Copy the provided **External Database URL**.

### 2. Fork or Push Repository to GitHub
- Ensure your project root contains `render.yaml`, `requirements.txt`, `create_superuser.py`, and the entire codebase.

### 3. Deploy Web Service using Render Blueprint
- Create a new **Blueprint** service on Render and link your GitHub repository.
- Render will parse `render.yaml` to deploy:
  - Runtime: Python 3.11.9
  - Build command: `pip install -r requirements.txt && python manage.py collectstatic --no-input && python manage.py migrate && python create_superuser.py`
  - Start command: `gunicorn restaurant_project.wsgi:application`
- **Alternatively**, create a manual Web Service on Render:
  - Environment: Python
  - Build Command: `pip install -r requirements.txt && python manage.py collectstatic --no-input && python manage.py migrate && python create_superuser.py`
  - Start Command: `gunicorn restaurant_project.wsgi:application`

### 4. Configure Production Environment Variables on Render
Add the following Environment Variables in the Render settings dashboard:
- `SECRET_KEY`: (auto-generated or secure string)
- `DEBUG`: `False`
- `DATABASE_URL`: `postgres://user:pass@host:port/dbname`
- `ALLOWED_HOSTS`: `<your-render-subdomain>.onrender.com`
- `CSRF_TRUSTED_ORIGINS`: `https://<your-render-subdomain>.onrender.com`
- `ADMIN_USERNAME`: `production_admin`
- `ADMIN_EMAIL`: `admin@smartdine.com`
- `ADMIN_PASSWORD`: (your secure production password)
- `WEB_CONCURRENCY`: `2` (conservative worker limits for 512 MB memory constraints)

---

## Security Configurations

- **Authoritative Database Pricing**: Client-side prices are completely ignored. Checkout totals are derived strictly from database prices.
- **CSRF Token Checks**: CSRF checking is enabled on all state-altering forms, including synchronizations and status transitions.
- **Workflow State Controls**: Sequential progression validation prevents skips or backwards adjustments: `RECEIVED → PREPARING → READY → COMPLETED`.
- **Database Row Lock Protection**: Employs row-level database locking using `select_for_update()` inside `transaction.atomic()` during status adjustments to safeguard against concurrent update race states.
- **Production Cookie Settings**: Production deployments enforce `SESSION_COOKIE_SECURE = True` and `CSRF_COOKIE_SECURE = True` when `DEBUG = False`.

---

## Testing Commands

Ensure code stability by executing tests before making modifications:

- **Run all tests**:
  ```powershell
  python manage.py test
  ```
- **Run restaurant app tests**:
  ```powershell
  python manage.py test restaurant
  ```
- **Run Django check**:
  ```powershell
  python manage.py check
  ```
- **Verify production readiness settings check**:
  ```powershell
  python manage.py check --deploy
  ```
