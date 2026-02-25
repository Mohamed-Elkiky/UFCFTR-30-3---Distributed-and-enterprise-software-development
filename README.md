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