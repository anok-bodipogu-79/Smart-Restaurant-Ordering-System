# Production Operations Guide

This guide describes operational procedures, monitoring endpoints, logging infrastructure, CI/CD pipelines, and configuration management for the Smart Restaurant Food Ordering & Kitchen Dashboard project in production.

---

## 1. Health Monitoring & Observability

The application features dedicated infrastructure-level health monitoring endpoints to support container health checks, orchestrator probes, and load balancer checks.

### Liveness Probe (`/health/`)
* **Purpose**: Verifies that the application process is running and able to handle HTTP traffic (process-level check).
* **HTTP Method**: GET
* **Authentication**: Excluded/Bypassed
* **Response Status**: `200 OK` (when process is alive)
* **Response Header**: `Cache-Control: no-store, no-cache, must-revalidate, max-age=0` (ensures results are never cached by intermediaries)
* **Payload**:
  ```json
  {"status": "ok"}
  ```

### Readiness Probe (`/health/ready/`)
* **Purpose**: Verifies that the application's external dependencies (the database) are healthy and ready to accept transactions.
* **HTTP Method**: GET
* **Authentication**: Excluded/Bypassed
* **Mechanism**: Executes a lightweight query `SELECT 1;` through Django's default database connection.
* **Response Status**:
  * `200 OK` (Database connection is healthy)
  * `503 Service Unavailable` (Database is unreachable or misconfigured)
* **Response Header**: `Cache-Control: no-store, no-cache, must-revalidate, max-age=0`
* **Successful Payload**:
  ```json
  {"status": "ready", "database": "ok"}
  ```
* **Failure Payload**:
  ```json
  {"status": "unavailable", "database": "error"}
  ```
  *(Note: Details of database traceback/exception stack are suppressed from the JSON response to prevent information disclosure. The actual exception is printed to the container stdout logs.)*

---

## 2. Logging Architecture

The application uses Django's native logging framework, configured to output directly to the console (`stdout`/`stderr`), making it optimized for containerized deployments (such as Render, Heroku, or Kubernetes log collectors).

### Configuration Parameters
* **Environment Control**: `LOG_LEVEL` environment variable controls logger verbosity.
  * **Allowed Values**: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`
  * **Default**: `INFO` (in production)
* **Formatter**: The verbose logs format is: `[%(asctime)s] %(levelname)s [%(name)s:%(lineno)s] %(message)s`
* **Log Propagation Control**: The custom `restaurant` logger explicitly sets `propagate: False` to prevent duplicate log records in standard outputs.

## 3. Managing Users and Roles (RBAC)

The system utilizes strict Role-Based Access Control via Django Groups. The normal operation of the restaurant strictly relies on standard user accounts assigned to explicit groups. 

### Roles:
* **Kitchen Staff**: Can access only the Kitchen Dashboard to process active orders.
* **Managers**: Can access only the Manager Console for analytics and menu modifications.
* **Superuser**: Must only be used for Django Administration and system configurations.

### 3.1 Generating Demo Accounts for Testing
During development or staging, you can automatically provision operational accounts by running:
```bash
python manage.py create_demo_users
```
This will idempotently generate `kitchen_demo` (password: `kitchenpass123`) in the `Kitchen Staff` group, and `manager_demo` (password: `managerpass123`) in the `Managers` group.

### 3.2 Provisioning Production Staff Accounts
In a live production environment:
1. Log into the **Django Admin Panel** using the superuser account.
2. Navigate to **Users** and click **Add User**.
3. Set the username and secure temporary password. Click **Save**.
4. In the user edit screen, scroll to the **Permissions** section.
5. In the **Groups** box, select either `Kitchen Staff` or `Managers`, and move it to the **Chosen groups** box using the arrow.
6. **Important**: DO NOT check `Staff status` or `Superuser status` for standard Kitchen or Manager employees. Their access is explicitly handled by group membership, maintaining strict separation of powers.
7. Click **Save**.

### Sensitive Data Masking & PII Protection
* Logs must **never** record passwords, security tokens, browser session IDs, cookie keys, or raw customer PII such as names and phone numbers.
* Operations (like checkouts or cancellations) are logged utilizing order database IDs and transaction metrics only:
  * **Correct**: `[2026-07-07 00:30:09] INFO [restaurant.views:230] Order #1 placed successfully with total amount 640.50.`
  * **Incorrect**: `[2026-07-07 00:30:09] INFO [restaurant.views:230] Order #1 placed for John Doe (+919876543210).`

---

## 4. GitHub Actions CI/CD Pipeline

The project includes an automated quality assurance pipeline defined in `.github/workflows/ci.yml`.

### Triggers
* Triggered automatically on every `push` and `pull_request` to `main` and `master` branches.

### Service Containers
* Spins up a **PostgreSQL 15** service container to execute integration checks and database migrations validation against a production-grade engine.

### Verification Steps
1. **Checkout Code**: Retrieves the repository branch.
2. **Setup Python**: Installs Python `3.13` and caches pip packages to accelerate builds.
3. **Install Dependencies**: Installs requirements from `requirements.txt`.
4. **Verify Migrations State**: Runs `python manage.py makemigrations --check --dry-run` to ensure all database migrations are created and checked in.
5. **Run System Checks**: Runs Django's system validator (`python manage.py check`).
6. **Validate Production Configuration**: Runs deploy checks (`python manage.py check --deploy`) under `DEBUG=False` with a production-safe key override.
7. **Execute Test Suite**: Runs Django test suite (`python manage.py test`) against the PostgreSQL service container with `DB_SSL_REQUIRE=False`.
8. **Static Files Check**: Validates `python manage.py collectstatic --no-input` runs cleanly.

---

## 4. Automatic Superuser Provisioning

The `create_superuser.py` script automatically creates an administrator user at startup.

### Environment Requirements
To automatically create the administrator, configure the following variables in the environment:
* `ADMIN_USERNAME`: The admin username (e.g. `admin`).
* `ADMIN_EMAIL`: The admin email address (e.g. `admin@example.com`).
* `ADMIN_PASSWORD`: A strong, secure admin password.

### Hardened Production Behavior
* **Development Mode (`DEBUG=True`)**: If environment parameters are missing, the script prints a warning and exits cleanly (exit code `0`) to simplify developer setups.
* **Production Mode (`DEBUG=False`)**: If any of the admin credentials (`ADMIN_USERNAME`, `ADMIN_EMAIL`, or `ADMIN_PASSWORD`) are missing or blank, the script **fails immediately** with exit code `1` and prints an error to stderr. This prevents silent bypasses and ensures production access is explicitly secured.

---

## 6. PostgreSQL Deployment Configuration

* **Database Routing**: Falls back automatically to local SQLite during development when `DATABASE_URL` is omitted, and uses PostgreSQL dynamically when `DATABASE_URL` is configured.
* **SSL Requirement Override**: In production, the DB driver requires SSL connection parameters (`ssl_require=True`) by default. To connect to PostgreSQL service containers in CI or on-premise deployments without SSL, set the environment variable:
  ```env
  DB_SSL_REQUIRE=False
  ```

---

## 7. Media Storage & Upload Architecture

### Local Development
In development (`DEBUG=True`), uploaded MenuItem food images are saved to the local file system under the `media/` directory (`MEDIA_ROOT`) and served by Django's static media server.

### Production Environment (Outcome B)
Render web service filesystems are ephemeral. Any local file uploads will be lost upon service restart, deployment, or automatic node replacement. 

To enable production-safe persistent storage, the storage engine should be configured to run with an external object/cloud storage provider such as **Cloudinary** or **Amazon S3**.

#### Required Configuration Steps for Cloudinary
1. Install `django-cloudinary-storage` dependency.
2. In `settings.py`, configure:
   ```python
   STORAGES = {
       "default": {
           "BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage",
       },
       "staticfiles": {
           "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
       },
   }
   ```
3. Set the following environment variables in the Render console:
   - `CLOUDINARY_CLOUD_NAME`: (Your Cloudinary Cloud Name)
   - `CLOUDINARY_API_KEY`: (Your Cloudinary API Key)
   - `CLOUDINARY_API_SECRET`: (Your Cloudinary API Secret)
