import os
from pathlib import Path
from django.core.management.base import BaseCommand
import cloudinary
import cloudinary.uploader
from restaurant.models import MenuItem


class Command(BaseCommand):
    help = "Uploads all menu item images from local media/menu_items/ to Cloudinary and verifies database links."

    def add_arguments(self, parser):
        parser.add_argument('--cloud-name', type=str, help='Cloudinary Cloud Name')
        parser.add_argument('--api-key', type=str, help='Cloudinary API Key')
        parser.add_argument('--api-secret', type=str, help='Cloudinary API Secret')

    def handle(self, *args, **options):
        cloud_name = options.get('cloud_name') or os.environ.get('CLOUDINARY_CLOUD_NAME')
        api_key = options.get('api_key') or os.environ.get('CLOUDINARY_API_KEY')
        api_secret = options.get('api_secret') or os.environ.get('CLOUDINARY_API_SECRET')

        if not cloud_name or not api_key or not api_secret:
            self.stderr.write(self.style.ERROR(
                "\n[ERROR] Missing Cloudinary credentials!\n"
                "Please configure CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, and CLOUDINARY_API_SECRET in your .env file,\n"
                "or pass them as flags: python manage.py upload_to_cloudinary --cloud-name <name> --api-key <key> --api-secret <secret>\n"
            ))
            return

        cloudinary.config(
            cloud_name=cloud_name,
            api_key=api_key,
            api_secret=api_secret,
            secure=True,
        )

        media_dir = Path("media/menu_items")
        if not media_dir.exists():
            self.stderr.write(self.style.ERROR(f"Directory {media_dir} does not exist."))
            return

        image_files = list(media_dir.glob("*.png")) + list(media_dir.glob("*.jpg")) + list(media_dir.glob("*.jpeg")) + list(media_dir.glob("*.webp"))

        if not image_files:
            self.stdout.write(self.style.WARNING("No images found in media/menu_items/."))
            return

        self.stdout.write(self.style.NOTICE(f"Found {len(image_files)} image(s) to upload to Cloudinary '{cloud_name}'...\n"))

        success_count = 0
        for img_path in sorted(image_files):
            stem = img_path.stem
            filename = img_path.name
            target_public_id = f"media/menu_items/{stem}"
            db_image_relpath = f"menu_items/{filename}"

            self.stdout.write(f"Uploading {filename} ... ", ending="")
            try:
                res = cloudinary.uploader.upload(
                    str(img_path),
                    public_id=target_public_id,
                    overwrite=True,
                    resource_type="image",
                    use_filename=True,
                    unique_filename=False,
                )
                secure_url = res.get("secure_url")
                self.stdout.write(self.style.SUCCESS("OK!"))
                self.stdout.write(f"  -> Cloudinary URL: {secure_url}")
                success_count += 1

                # Update any MenuItem in database matching this image name
                matching_items = MenuItem.objects.filter(image__icontains=filename)
                for item in matching_items:
                    item.image = db_image_relpath
                    item.save(update_fields=['image'])
                    self.stdout.write(f"  -> Linked to MenuItem #{item.id} ({item.name})")

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"FAILED ({e})"))

        self.stdout.write(self.style.SUCCESS(f"\nFinished: {success_count}/{len(image_files)} images uploaded successfully to Cloudinary!"))
