import os
import sys

def create_admin():
    # Set settings module
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "restaurant_project.settings")
    
    # Initialize Django
    import django
    django.setup()
    
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    from django.conf import settings
    
    # Read environment variables
    username = os.environ.get("ADMIN_USERNAME")
    email = os.environ.get("ADMIN_EMAIL")
    password = os.environ.get("ADMIN_PASSWORD")
    
    if not username or not email or not password:
        if not settings.DEBUG:
            print("ERROR: Automatic superuser creation failed in production. ADMIN_USERNAME, ADMIN_EMAIL, and ADMIN_PASSWORD environment variables must be explicitly configured.", file=sys.stderr)
            sys.exit(1)
        else:
            print("Automatic superuser creation skipped: missing required ADMIN_USERNAME, ADMIN_EMAIL, or ADMIN_PASSWORD. This is allowed in development mode.")
            sys.exit(0)
        
    try:
        # Check if user already exists
        if User.objects.filter(username=username).exists():
            print(f"Superuser '{username}' already exists. Skipping creation.")
            sys.exit(0)
            
        # Create superuser
        User.objects.create_superuser(username=username, email=email, password=password)
        print(f"Superuser '{username}' created successfully!")
        
    except Exception as e:
        print(f"Error occurred during superuser creation: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    create_admin()
