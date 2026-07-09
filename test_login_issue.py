import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "restaurant_project.settings")
django.setup()

from django.test import Client
from django.contrib.auth.models import User

# Check if user exists and is active
user = User.objects.get(username="testkitchen_new")
print(f"User: {user.username}, Active: {user.is_active}, Staff: {user.is_staff}, Groups: {[g.name for g in user.groups.all()]}")

c = Client(SERVER_NAME='localhost')
response = c.post('/kitchen/login/', {'username': 'testkitchen_new', 'password': 'kitchenpass123'})

if response.status_code == 302:
    print(f"SUCCESS: Redirected to {response.url}")
else:
    print(f"FAILED: Status code {response.status_code}")
    if response.context and 'form' in response.context:
        print(f"Errors: {response.context['form'].errors}")
