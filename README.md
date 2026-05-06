# BRFN Marketplace Platform

Distributed and enterprise software development project for a regional food network marketplace. The platform supports multi-role users, multi-vendor ordering, recurring orders, seasonal product logic, logistics calculations, reviews, notifications, and producer payouts.

## Tech Stack

- Python 3.11
- Django 4.2.11
- PostgreSQL
- Docker and Docker Compose
- pytest and pytest-django

## Project Structure

Core Django apps:

- apps/accounts: authentication and role-based profiles
- apps/cart: cart and pricing logic
- apps/common: shared permissions and validators
- apps/content: CMS pages and product-linked content
- apps/logistics: geocoding and food miles
- apps/marketplace: product catalog, search, seasonal and surplus flows
- apps/notifications: in-app notifications
- apps/orders: customer, producer, and recurring order flows
- apps/payments: payment and commission logic
- apps/reviews: product reviews and ratings

Other key folders:

- templates: Django templates for all features
- static: CSS and JavaScript assets
- fixtures: seed data
- tests: shared factories and test helpers

## User Roles

- admin
- producer
- customer
- community_group

Community groups are allowed through buyer-only routes via shared customer permission handling.

## Key Features

### Marketplace

- Product catalog, category browsing, search, and filtering
- Organic and in-season filters
- Product detail with food miles and reviews

### Orders

- Single cart checkout across multiple producers
- Producer-level sub-orders and commission split
- Order status transitions and reorder flow

### Recurring Orders

- Create recurring templates with RRULE strings
- Generate upcoming instances
- Modify next instance quantities
- Quantity overrides are persisted on RecurringOrderInstance as JSON
- Scheduler command: generate_recurring_instances

### Community Group Buying

- Dedicated registration endpoint
- Organisation type capture in registration form
- Buyer permission parity with customer flows

### Seasonal and Surplus Logic

- Seasonal availability states on products
- Surplus deal creation and discounted pricing
- Seasonal tests and surplus tests in marketplace test suite

## Season-Based Product Selector

The dynamic product selector and API are season-based.

- API endpoint: /marketplace/api/products/
- Seasonal query parameter: in_season=true
- Backend filter: Product.AvailabilityStatus.IN_SEASON
- Frontend default: in-season checkbox checked

The selector does include an available flag in API response payload for display badges, but filtering for selector fetches is driven by in_season.

## Local Setup (Without Docker)

1. Create and activate a virtual environment.
2. Install dependencies.
3. Configure environment variables for database connection.
4. Run migrations.
5. Optionally load seed data.
6. Start the server.

Commands:

python -m venv venv

Windows:
venv\Scripts\activate

Mac/Linux:
source venv/bin/activate

pip install -r requirements.txt
python manage.py migrate
python manage.py loaddata fixtures/seed.json
python manage.py runserver

## Docker Setup

Build and run:

docker-compose up --build

Stop:

docker-compose down

Create superuser:

docker-compose exec web python manage.py createsuperuser

Run migrations:

docker-compose exec web python manage.py migrate

Run tests:

docker-compose exec web pytest -q

## Common Development Commands

Create migrations:

python manage.py makemigrations

Apply migrations:

python manage.py migrate

Run Django system checks:

python manage.py check

Run all tests:

pytest

Run marketplace seasonal tests:

pytest apps/marketplace/tests/test_seasonal.py -v

Run marketplace test suite:

pytest apps/marketplace/tests/ -v

Generate recurring instances manually:

python manage.py generate_recurring_instances --days=7 --verbose

Dry-run recurring generation:

python manage.py generate_recurring_instances --dry-run --verbose

Mark an order delivered:

python manage.py deliver_order --order-id <order_uuid>

Run weekly settlement:

python manage.py run_weekly_settlement

## Database Access (Docker)

Open Postgres shell:

docker-compose exec db psql -U myuser -d mydb

Query user emails:

psql "postgresql://myuser:mypassword@localhost:5432/mydb" -c "SELECT id, email FROM accounts_user ORDER BY id DESC LIMIT 20;"

## Recurring Scheduler Operations

Recommended daily job (example, 1 AM):

0 1 * * * python manage.py generate_recurring_instances --days=14

If using Celery beat, wire a periodic task that calls the same command or service function.

## API Notes

### Products API for dynamic selector

Route:

/marketplace/api/products/

Supported query parameters:

- in_season=true
- producer_id=<uuid>
- category_id=<id>
- search=<text>
- limit=<int>
- page=<int>

Example:

/marketplace/api/products/?in_season=true&search=tomato&limit=50

## Testing Guidance

Focus areas covered in tests include:

- Seasonal availability transitions
- Surplus discount behavior
- Cart total pricing effects
- Recurring template and instance logic
- Role and permission behavior

## Deployment Checklist

1. Use Python 3.11 runtime.
2. Install dependencies from requirements.txt.
3. Apply migrations.
4. Load required seed data.
5. Set DEBUG to false for production.
6. Collect static files.
7. Configure recurring scheduler job.
8. Run smoke tests across all user roles.

## Troubleshooting

- If recurring instances are missing, run the scheduler command manually in verbose mode.
- If community group users are blocked from buyer pages, verify role and profile records.
- If seasonal selector results look wrong, confirm API requests include in_season=true.
- If product filtering is empty, check product availability state values in database.

## Notes for Contributors

- Prefer service-layer logic in apps/*/services for business rules.
- Keep permission decorators consistent with role model changes.
- Add or update tests when changing checkout, seasonal, or recurring behavior.
- Keep documentation in this README aligned with implemented routes and management commands.