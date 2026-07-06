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
    
    # Read environment variables
    username = os.environ.get("ADMIN_USERNAME")
    email = os.environ.get("ADMIN_EMAIL")
    password = os.environ.get("ADMIN_PASSWORD")
    
    if not username or not email or not password:
        print("Automatic superuser creation skipped: missing required ADMIN_USERNAME, ADMIN_EMAIL, or ADMIN_PASSWORD environment variables.")
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
