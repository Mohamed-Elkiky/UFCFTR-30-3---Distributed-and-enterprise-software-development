from django.db import models

# No database models required for the logistics app.
# TC-013 (Food Miles) geo data is stored directly on account profiles:
#   - apps.accounts.ProducerProfile  → latitude, longitude, postcode
#   - apps.accounts.CustomerProfile  → latitude, longitude, postcode
# Distance calculation logic lives in apps/logistics/services/