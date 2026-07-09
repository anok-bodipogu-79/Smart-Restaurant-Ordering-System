# SmartDine – Smart Restaurant Ordering System
## Comprehensive Project Report & Technical Documentation

---

## 1. Executive Summary
**SmartDine** is a modern, full-stack Django web application designed to streamline restaurant operations and elevate the customer dining experience. By integrating a seamless customer-facing ordering workflow, a real-time kitchen intelligence dashboard, a robust manager analytics suite, and a digital receipt engine, SmartDine serves as a complete digital operating system for modern hospitality.

The application underwent a comprehensive UI/UX overhaul to implement the **SmartDine Premium Hospitality UI** design language. This design is characterized by a singular, elegant light theme featuring warm minimalism, editorial typography, structured Bento-style grids, deep forest green primary accents, and burnished gold highlights, replacing legacy multi-theme interfaces with a premium, cohesive brand identity.

---

## 2. Objectives & Problem Statement
### The Problem
Traditional restaurants often struggle with disjointed workflows:
- Waitstaff and kitchen miscommunication leading to delayed or incorrect orders.
- Customers lacking visibility into their order status.
- Management lacking real-time insights into revenue, prep times, and inventory popularity.
- Fragmented software where menus, point-of-sale (POS), and kitchen displays (KDS) are handled by different, incompatible systems.

### The Solution
SmartDine unifies these disparate processes into a single web-based platform:
- **Customers** order via their devices and track status in real time.
- **Kitchen Staff** receive digital tickets, process them chronologically, and update states with a single click.
- **Managers** oversee the entire operation via a centralized, role-protected dashboard providing live KPIs, menu management, and immutable audit logs.

---

## 3. Technology Stack & System Architecture
SmartDine is built on a decoupled monolithic architecture, chosen for its rapid development cycle, strong security defaults, and cohesive server-rendered templates.

### Backend Layer
- **Framework**: Django 5.x (Python-based MTV architecture).
- **Database**: SQLite (Development) / PostgreSQL (Production-ready capability).
- **ORM**: Django Object-Relational Mapping for database queries, schema migrations, and relational integrity.
- **Authentication**: Built-in Django Auth system utilizing PBKDF2 password hashing.

### Frontend Layer
- **Markup & Layout**: Semantic HTML5 and Bootstrap 5.3.3 grid system.
- **Styling**: Vanilla CSS3 utilizing a robust CSS Custom Properties (Variables) design system. Tailwind was deliberately avoided to maintain granular, bespoke control over the premium aesthetic.
- **Interactivity**: Vanilla JavaScript handles dynamic DOM updates, cart mutations, and UI transitions without the overhead of heavy frameworks like React or Vue.
- **Icons**: Bootstrap Icons (SVG format).

---

## 4. Database Schema & Entity-Relationship Design
The application relies on six core models defined in `restaurant/models.py`. The schema is highly normalized while intentionally snapshotting financial data for historical integrity.

### 4.1. Core Models
1. **Category**: Groups menu items.
   - Fields: `id`, `name` (CharField), `icon` (CharField for Bootstrap Icons).
2. **MenuItem**: Individual offerings.
   - Fields: `id`, `category` (FK), `name`, `description`, `price` (DecimalField), `image_url`, `image` (ImageField), `is_available`, `is_vegetarian`, `is_spicy`.
3. **Order**: Represents a customer transaction.
   - Fields: `id`, `customer_name`, `customer_phone`, `table_number`, `status` (Choices: RECEIVED, PREPARING, READY, COMPLETED, CANCELLED), `tracking_token` (UUID4), financial fields (`subtotal_amount`, `tax_amount`, `tax_rate`, `total_amount`), timestamps.
4. **OrderItem**: Bridges Orders and MenuItems (Many-to-Many through table).
   - Fields: `order` (FK), `menu_item` (FK), `quantity`, `instructions`.
   - **Historical Integrity Fields**: `item_name_at_order`, `category_name_at_order`, `price_at_order`.
5. **AuditLog**: Immutable system ledger.
   - Fields: `id`, `timestamp`, `actor` (FK to User), `action`, `target_type`, `target_id`, `description`.

### 4.2. Schema Design Principles
- **Financial Immutability**: By storing `price_at_order` inside the `OrderItem`, the system ensures that if a manager updates a menu item's price tomorrow, yesterday's receipts and revenue analytics remain strictly accurate.
- **Session-Independent Tracking**: The `tracking_token` (UUID) allows customers to access their active orders from any device without requiring user accounts or persisting cookies.

---

## 5. Detailed Feature Breakdown

### A. Customer Menu & Ordering Workflow
- **Advanced Discovery**: Real-time filtering by text query, category, dietary preference (`is_vegetarian`), heat index (`is_spicy`), and availability.
- **Dynamic Sorting**: Customers can sort the catalog by Price (Low/High), Name (A-Z), and Popularity (computed dynamically based on order volume).
- **Session-Based Cart**: Users can add items, specify special instructions (e.g., "Allergy: Peanuts", "Extra spicy"), and modify quantities. The cart relies on Django sessions.
- **Frictionless Checkout**: Form validation mandates a valid customer name, normalizes Indian phone numbers (e.g., converting local formats to `+91XXXXXXXXXX`), and accepts optional table numbers for dine-in tracking.

### B. Kitchen Intelligence Dashboard (Phase B)
- **Chronological Queuing System**: Active orders are categorized into columns (`RECEIVED`, `PREPARING`, `READY`) and sorted oldest-first to prevent ticket stagnation.
- **Strict State Machine**: The order workflow enforces directional integrity:
  - `RECEIVED` $\rightarrow$ `PREPARING` $\rightarrow$ `READY` $\rightarrow$ `COMPLETED`
  - Attempts to skip states (e.g., `RECEIVED` directly to `COMPLETED`) or move backward are rejected by backend validation logic.
- **Real-time Synchronization**: The UI clearly displays special instructions directly on the tickets so chefs don't miss dietary requests.

### C. Manager Analytics & Control Center (Phase C)
- **Live Business Intelligence**: The dashboard computes KPIs over selectable intervals (Today, 7 days, 30 days, Custom). Metrics include:
  - **Revenue**: Sum of completed/active order totals.
  - **Order Volume**: Total transactions.
  - **Cancellation Rate**: Percentage of orders marked as `CANCELLED`.
  - **Average Prep Time**: The time elapsed between a `RECEIVED` status and a `READY`/`COMPLETED` status.
- **Catalog Control**: Full CRUD interfaces for Menu Items and Categories. Managers can instantly toggle availability to `False` if an item sells out.
- **Audit Trail UI**: Managers can view the read-only Audit Logs to track which staff member cancelled an order or changed a price.

### D. Digital Receipts (Phase D)
- **Responsive Generation**: Generates a visually clean, layout-stable digital receipt.
- **Print Optimization**: Utilizes CSS `@media print` rules to strip navigation elements and format the width perfectly for 80mm thermal receipt printers.

---

## 6. Security & Role-Based Access Control (RBAC)
SmartDine enforces strict isolation between Customer, Kitchen, and Manager contexts.

### 6.1. Custom Authorization Mixins
Instead of relying solely on Django's generic `is_staff` boolean, SmartDine utilizes precise group-based checks:
- **`KitchenRequiredMixin`**: Verifies the authenticated user belongs to the `"Kitchen Staff"` Django Group.
- **`ManagerRequiredMixin`**: Verifies the authenticated user belongs to the `"Managers"` Django Group.

### 6.2. Authentication Redesign
- Implemented **Asymmetric Bento Authentication** screens.
- Separated login endpoints (`/kitchen/login/` and `/manager/login/`) to prevent URL snooping and enforce strict redirection to the appropriate dashboards.
- Internal dashboards are completely decoupled from the public customer navigation to prevent confusion.

### 6.3. Audit Logging Security
The `AuditLog` model is locked down even within the built-in Django Admin. Custom `ModelAdmin` permissions (`has_add_permission`, `has_change_permission`, `has_delete_permission`) are explicitly hardcoded to return `False`, ensuring the audit trail remains immutable.

---

## 7. UI/UX Design System Specifications
The frontend was completely refactored to remove legacy dark modes and generic styling, adopting the **SmartDine Premium Hospitality UI**.

### 7.1. Color Tokens
- **Backgrounds**: `Warm Ivory` (`#FAF9F5`), Clean White (`#FFFFFF`) for cards.
- **Primary Brand**: `Deep Forest Green` (`#245A4C`, `#173F35`).
- **Accents**: `Burnished Gold` (`#C5A880`, `#D4B895`) for interactive highlights and premium badges.
- **Borders & Shadows**: Subtle glassmorphism with `backdrop-filter: blur(8px)` and highly feathered box-shadows (`rgba(36, 90, 76, 0.06)`).

### 7.2. Typography & Layout
- **Typefaces**: `Manrope` for all highly readable UI text, buttons, and numeric data. Editorial serif combinations used for branding elements.
- **Bento Grid**: Dashboards employ structured, asymmetric grid layouts (Bento UI) that compartmentalize analytics, recent orders, and actions into distinct, scannable blocks.
- **Micro-Animations**: Smooth CSS transitions (`0.25s ease`) on button hovers, card lifts, and modal reveals.

---

## 8. Testing & Quality Assurance
SmartDine maintains exceptional reliability through a comprehensive automated test suite (over 170 individual assertions).

- **Unit Testing**: Covers individual model methods, form validation logic, and field constraints.
- **Integration & Workflow Testing**:
  - `test_kitchen.py`: Verifies kitchen authorization blocks non-staff users and tests the sequential status transition logic.
  - `test_manager.py`: Tests the analytics computation engine, ensuring revenue and prep times calculate correctly over varying date ranges.
  - `test_tracking.py`: Ensures UUIDs securely obscure order details from unauthorized viewers.
- **Command**: Run the full suite via `python manage.py test restaurant`.

---

## 9. Deployment & Installation Guide

### Prerequisites
- Python 3.10+
- pip (Python Package Installer)

### Local Setup Instructions
1. **Clone & Virtual Environment**:
   ```bash
   python -m venv venv
   # Windows
   .\venv\Scripts\activate
   # macOS/Linux
   source venv/bin/activate
   ```

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Database Migration**:
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

4. **Initialize Core Data & Users**:
   Populate the database with the default menu, categories, and test user accounts (Manager, Kitchen Staff):
   ```bash
   python manage.py create_demo_users
   ```

5. **Run Development Server**:
   ```bash
   python manage.py runserver
   ```
   *Access the Customer Menu at `http://127.0.0.1:8000/`*
   *Access the Staff Portal at `http://127.0.0.1:8000/staff/`*

---
*End of Report*
