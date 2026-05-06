# Bristol Regional Food Network — Digital Marketplace

A Django-based multi-vendor marketplace connecting local food producers with customers in the Bristol region. Built with Docker multi-container architecture (PostgreSQL + Django/Gunicorn + Nginx).

**Module:** UFCFTR-30-3 Distributed & Enterprise Software Development  
**Group:** DESD Group 2

## Team

| Name | Student ID 
|------|------------
| Mohamed Elkiky | 21068307 |
| Sergio Salas | 23039230 |
| Kirill Gontar | 23077530 |
| Konstantinos Demetriou | 23004235

## Architecture

The application uses a three-container Docker architecture:

- **db** — PostgreSQL 15 database
- **web** — Django 4.2 application served by Gunicorn (WSGI)
- **nginx** — Nginx reverse proxy serving static/media files and forwarding requests to Gunicorn

## Quick Start

```bash
# Clone the repository
git clone https://github.com/Mohamed-Elkiky/UFCFTR-30-3---Distributed-and-enterprise-software-development.git
cd UFCFTR-30-3---Distributed-and-enterprise-software-development

# Build and start all containers
docker compose up --build

# The site is available at http://localhost
```

On first run, the entrypoint automatically:
1. Waits for PostgreSQL to be ready
2. Runs Django migrations
3. Collects static files for Nginx
4. Loads seed data from `fixtures/seed.json` (if the database is empty)

## Default Accounts

| Role | Email | Password |
|------|-------|----------|
| Admin | admin@brfn.com | Admin123 |

Producer and customer accounts are created via the registration pages or loaded from seed data. See `producer_accounts.txt` for pre-seeded producer credentials.

## Common Commands

```bash
# Stop all containers
docker compose down

# Reset database and rebuild (after model/migration changes)
docker compose down -v && docker compose up --build

# Run the test suite
docker compose exec web pytest -q

# Create a superuser
docker compose exec web python manage.py createsuperuser

# Run weekly settlement processing
docker compose exec web python manage.py run_weekly_settlement

# Generate recurring order instances
docker compose exec web python manage.py generate_recurring_instances --days=7

# Access the database shell
docker compose exec db psql -U myuser -d mydb
```

## Test Cases

The system implements all 25 test cases defined in `Test_Cases.pdf`:

| ID | Feature | Priority |
|----|---------|----------|
| TC-001 | Producer registration | Critical |
| TC-002 | Customer registration | Critical |
| TC-003 | Product listing with seasonal availability | Critical |
| TC-004 | Browse products by category | Critical |
| TC-005 | Search by name, description, producer | High |
| TC-006 | Shopping cart with quantity management | Critical |
| TC-007 | Single-producer checkout | Critical |
| TC-008 | Multi-vendor checkout with payment distribution | Critical |
| TC-009 | Producer order dashboard | Critical |
| TC-010 | Order status updates with notifications | High |
| TC-011 | Inventory and stock management | High |
| TC-012 | Weekly payment settlements (95% to producers) | Critical |
| TC-013 | Food miles calculation | Medium |
| TC-014 | Organic certification filter | Medium |
| TC-015 | Allergen warnings (UK 14 major allergens) | Critical |
| TC-016 | Seasonal availability with date ranges | High |
| TC-017 | Community group bulk orders | Medium |
| TC-018 | Restaurant recurring weekly orders | Medium |
| TC-019 | Surplus produce discounts | Medium |
| TC-020 | Recipes and farm stories | Low |
| TC-021 | Order history with reorder | High |
| TC-022 | Secure authentication and RBAC | Critical |
| TC-023 | Low stock notifications | Medium |
| TC-024 | Product ratings and reviews | Medium |
| TC-025 | Commission monitoring and financial reports | High |

## Running Tests

```bash
docker compose exec web pytest -q
```

Tests are organised by app:

- `apps/accounts/tests/` — Registration (TC-001, TC-002, TC-017), Auth/RBAC (TC-022)
- `apps/marketplace/tests/` — Products, cart, orders, payments, reviews, surplus, content, notifications
- `apps/logistics/tests/` — Food miles (TC-013)
- `apps/payments/tests/` — Mock payment gateway (TC-007)
- `tests/` — Factory smoke tests

## Technology Stack

- **Backend:** Django 4.2, Django REST Framework
- **Database:** PostgreSQL 15
- **WSGI Server:** Gunicorn
- **Reverse Proxy:** Nginx
- **Containerisation:** Docker, Docker Compose
- **Testing:** pytest, factory-boy
- **Payment:** Mock gateway (test sandbox)
- **Geocoding:** Postcode-based distance calculation for food miles

## Project Structure

```
├── apps/
│   ├── accounts/       # User registration, authentication, profiles (TC-001, TC-002, TC-022)
│   ├── cart/           # Shopping cart and checkout (TC-006, TC-007, TC-008)
│   ├── common/         # Shared permissions (RBAC decorators)
│   ├── content/        # Recipes, farm stories (TC-020)
│   ├── logistics/      # Food miles calculation (TC-013)
│   ├── marketplace/    # Products, categories, search, surplus deals (TC-003–TC-005, TC-014–TC-016, TC-019)
│   ├── notifications/  # Low stock alerts, order notifications (TC-023)
│   ├── orders/         # Order management, recurring orders (TC-009, TC-010, TC-018, TC-021)
│   ├── payments/       # Settlements, commission, mock gateway (TC-012, TC-025)
│   └── reviews/        # Product ratings and reviews (TC-024)
├── docker/
│   ├── nginx/          # Nginx reverse proxy configuration
│   └── postgres/       # PostgreSQL initialisation
├── fixtures/           # Seed data (seed.json)
├── templates/          # Django HTML templates
├── static/             # Static assets (CSS, JS)
├── docker-compose.yml  # Multi-container orchestration
├── Dockerfile          # Django application image
└── requirements.txt    # Python dependencies
```