# Create virtual environment
python -m venv venv

# Activate venv (Mac/Linux)
source venv/bin/activate

# Activate venv (Windows)
venv\Scripts\activate

# Install dependencies (if needed)
pip install -r requirements.txt

# Run Django server
python manage.py runserver

# Marketplace Migrations
python manage.py makemigrations marketplace
python manage.py migrate


# Start the project
docker-compose up

# Stop the project
docker-compose down

# Create admin user (if needed)
docker-compose exec web python manage.py createsuperuser

# Run migrations after model changes
docker-compose exec web python manage.py makemigrations
docker-compose exec web python manage.py migrate

# database viewing 
 docker-compose exec db psql -U myuser -d mydb
psql "postgresql://myuser:mypassword@localhost:5432/mydb"

# database selecting emails
 psql "postgresql://myuser:mypassword@localhost:5432/mydb" -c "SELECT id, email FROM accounts_user ORDER BY id DESC LIMIT 20;"

# test
docker-compose exec web pytest -q

# admin account login
user name = admin@brfn.com
password = Admin123


# if changes was made to db run
git pull
docker compose down -v
docker compose up --build
docker exec -it ufcftr-30-3---distributed-and-enterprise-software-development-web-1 python manage.py loaddata fixtures/seed.json

# command to make the order show up as delievered (swap out the fake order id with the real one that shows up when the order is delivered)
docker compose exec web python manage.py deliver_order --order-id a1b2c3d4-0001-0001-0001-000000000001
# command to get the latest order 
docker compose exec web python manage.py shell -c "from apps.orders.models import CustomerOrder; print(CustomerOrder.objects.latest('created_at').pk)"

# geocode test
docker exec -it ufcftr-30-3---distributed-and-enterprise-software-development-web-1 python manage.py shell -c "from apps.logistics.services.geocoding import geocode_postcode; print(geocode_postcode('BS1 4DJ'))"

# food miles distance calculation 
docker exec -it ufcftr-30-3---distributed-and-enterprise-software-development-web-1 python manage.py shell -c "
from apps.logistics.services.distance import haversine_miles, get_food_miles
from apps.marketplace.models import Product
from apps.accounts.models import CustomerProfile, ProducerProfile
from apps.logistics.services.geocoding import geocode_postcode
customer_lat, customer_lng = geocode_postcode('BS1 5JG')
for producer in ProducerProfile.objects.filter(latitude__isnull=False):
    miles = haversine_miles(producer.latitude, producer.longitude, customer_lat, customer_lng)
    print(f'{producer.business_name} ({producer.postcode}) -> {miles} miles from BS1 5JG')
"

# seasonal products
pytest apps/marketplace/tests/test_seasonal.py -v
Key things being tested:

Test	What it covers
Parametrised is_in_season	Normal range, wrap-around, boundary months
Missing months	Guards against None values
Year-round product	Non-seasonal products always return False
auto_update brings in season	DB round-trip, OUT_OF_SEASON → IN_SEASON
auto_update takes out of season	DB round-trip, IN_SEASON → OUT_OF_SEASON
Ignores year-round	AVAILABLE_YEAR_ROUND products untouched



# test surpluss deals
docker compose exec web python manage.py shell

from tests.factories import ProductFactory, ProducerProfileFactory, UserFactory
from apps.marketplace.services.surplus import create_surplus_deal, get_active_surplus_deals, apply_surplus_discount

# Create a producer + product
producer = ProducerProfileFactory()
product = ProductFactory(producer=producer, price_pence=1000, name="Test Apples")

# Create a 20% deal valid 24h
deal = create_surplus_deal(product, discount_percent=20, hours_valid=24, note="Selling fast!")

print("Active deals:", get_active_surplus_deals().count())  # 1
print("Original price:", product.price_pence)               # 1000
print("Discounted price:", apply_surplus_discount(product)) # 800

http://localhost:8000/surplus/

from tests.factories import ProductFactory, CustomerProfileFactory, CartFactory, CartItemFactory
from apps.marketplace.services.surplus import create_surplus_deal
from apps.cart.services.pricing import get_cart_total_pence

product = ProductFactory(price_pence=1000)
cart = CartFactory()
CartItemFactory(cart=cart, product=product, quantity=2)

print(get_cart_total_pence(cart))  # 2000 — no deal yet

create_surplus_deal(product, discount_percent=25, hours_valid=24)
print(get_cart_total_pence(cart))  # 1500 — 25% off × 2 items

from django.core.exceptions import ValidationError
try:
    create_surplus_deal(product, discount_percent=5, hours_valid=24)  # below 10%
except ValidationError as e:
    print(e)  # "discount_percent must be between 10 and 50"

from datetime import timedelta
from django.utils.timezone import now
from apps.marketplace.models import SurplusDeal
from apps.marketplace.services.surplus import expire_old_deals

# Manually expire the deal
SurplusDeal.objects.all().update(expires_at=now() - timedelta(hours=1))

print(get_active_surplus_deals().count())  # 0 — expired, not shown
expire_old_deals()                          # deletes it from DB
print(SurplusDeal.objects.count())          # 0

docker compose exec web pytest apps/marketplace/tests/ -v

# Build management command for weekly settlement (TC-012)
docker exec -it ufcftr-30-3---distributed-and-enterprise-software-development-web-1 python manage.py run_weekly_settlement