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
docker compose up

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
