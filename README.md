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
