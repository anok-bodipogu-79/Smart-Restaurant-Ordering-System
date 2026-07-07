import os
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

User = get_user_model()

class Command(BaseCommand):
    help = 'Creates demo users for Kitchen Staff and Managers groups'

    def handle(self, *args, **kwargs):
        kitchen_group, _ = Group.objects.get_or_create(name='Kitchen Staff')
        manager_group, _ = Group.objects.get_or_create(name='Managers')

        # Create Kitchen user
        kitchen_username = os.environ.get('DEMO_KITCHEN_USERNAME', 'kitchen_demo')
        kitchen_password = os.environ.get('DEMO_KITCHEN_PASSWORD', 'kitchenpass123')
        
        kitchen_user, created = User.objects.get_or_create(username=kitchen_username)
        if created:
            kitchen_user.set_password(kitchen_password)
            kitchen_user.save()
            self.stdout.write(self.style.SUCCESS(f"Created kitchen user: {kitchen_username}"))
        
        kitchen_user.groups.add(kitchen_group)
        self.stdout.write(self.style.SUCCESS(f"Added {kitchen_username} to Kitchen Staff group"))

        # Create Manager user
        manager_username = os.environ.get('DEMO_MANAGER_USERNAME', 'manager_demo')
        manager_password = os.environ.get('DEMO_MANAGER_PASSWORD', 'managerpass123')
        
        manager_user, created = User.objects.get_or_create(username=manager_username)
        if created:
            manager_user.set_password(manager_password)
            manager_user.save()
            self.stdout.write(self.style.SUCCESS(f"Created manager user: {manager_username}"))
        
        manager_user.groups.add(manager_group)
        self.stdout.write(self.style.SUCCESS(f"Added {manager_username} to Managers group"))

        self.stdout.write(self.style.SUCCESS("Successfully provisioned demo users."))
