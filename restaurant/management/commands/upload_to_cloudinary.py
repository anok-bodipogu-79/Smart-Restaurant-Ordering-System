import os
import urllib.request
import urllib.error
from pathlib import Path
from django.core.management.base import BaseCommand
import cloudinary
import cloudinary.uploader
from restaurant.models import MenuItem

MENU_ITEMS_MAPPING = [
    {"id": 1, "name": "Paneer Tikka", "image_file": "ChatGPT_Image_Jul_7_2026_10_36_36_AM.png"},
    {"id": 2, "name": "Chicken 65", "image_file": "ChatGPT_Image_Jul_7_2026_10_31_55_AM.png"},
    {"id": 3, "name": "Vegetable Spring Rolls", "image_file": "ChatGPT_Image_Jul_7_2026_10_38_19_AM.png"},
    {"id": 4, "name": "Gobi Manchurian", "image_file": "ChatGPT_Image_Jul_7_2026_10_35_13_AM.png"},
    {"id": 5, "name": "Chicken Biryani", "image_file": "ChatGPT_Image_Jul_7_2026_12_24_51_PM.png"},
    {"id": 6, "name": "Paneer Butter Masala", "image_file": "ChatGPT_Image_Jul_7_2026_12_25_00_PM.png"},
    {"id": 7, "name": "Vegetable Fried Rice", "image_file": "ChatGPT_Image_Jul_7_2026_12_25_07_PM.png"},
    {"id": 8, "name": "Butter Chicken", "image_file": "ChatGPT_Image_Jul_7_2026_12_24_41_PM.png"},
    {"id": 9, "name": "Gulab Jamun", "image_file": "ChatGPT_Image_Jul_7_2026_11_06_34_AM.png"},
    {"id": 10, "name": "Chocolate Brownie", "image_file": "ChatGPT_Image_Jul_7_2026_11_02_41_AM.png"},
    {"id": 11, "name": "Vanilla Ice Cream", "image_file": "ChatGPT_Image_Jul_7_2026_12_24_31_PM.png"},
    {"id": 12, "name": "Rasmalai", "image_file": "ChatGPT_Image_Jul_7_2026_11_32_03_AM.png"},
    {"id": 13, "name": "Masala Soda", "image_file": "ChatGPT_Image_Jul_7_2026_10_51_35_AM.png"},
    {"id": 14, "name": "Fresh Lime Juice", "image_file": "ChatGPT_Image_Jul_7_2026_10_45_54_AM.png"},
    {"id": 15, "name": "Cold Coffee", "image_file": "ChatGPT_Image_Jul_7_2026_10_41_44_AM.png"},
    {"id": 16, "name": "Mango Lassi", "image_file": "ChatGPT_Image_Jul_7_2026_10_47_54_AM.png"},
]


class Command(BaseCommand):
    help = "Uploads all menu item images from local media/menu_items/ to Cloudinary, updates PostgreSQL records, and verifies URLs."

    def add_arguments(self, parser):
        parser.add_argument('--cloud-name', type=str, help='Cloudinary Cloud Name')
        parser.add_argument('--api-key', type=str, help='Cloudinary API Key')
        parser.add_argument('--api-secret', type=str, help='Cloudinary API Secret')
        parser.add_argument('--force', action='store_true', help='Force re-upload of assets even if they exist on Cloudinary')
        parser.add_argument('--verify-only', action='store_true', help='Only verify delivery URLs without uploading')

    def check_asset_exists(self, url):
        """Checks whether an image asset is reachable via HTTP HEAD without downloading the payload."""
        try:
            req = urllib.request.Request(url, method='HEAD')
            with urllib.request.urlopen(req, timeout=5) as res:
                return res.status == 200, res.headers.get('Content-Type', '')
        except urllib.error.HTTPError as e:
            return False, f"HTTP {e.code}"
        except Exception as e:
            return False, f"Error: {e}"

    def handle(self, *args, **options):
        cloud_name = options.get('cloud_name') or os.environ.get('CLOUDINARY_CLOUD_NAME')
        api_key = options.get('api_key') or os.environ.get('CLOUDINARY_API_KEY')
        api_secret = options.get('api_secret') or os.environ.get('CLOUDINARY_API_SECRET')
        force = options.get('force', False)
        verify_only = options.get('verify_only', False)

        if not cloud_name or not api_key or not api_secret:
            self.stderr.write(self.style.ERROR(
                "\n[ERROR] Missing Cloudinary credentials!\n"
                "Please configure CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, and CLOUDINARY_API_SECRET in your environment,\n"
                "or pass flags: python manage.py upload_to_cloudinary --cloud-name <name> --api-key <key> --api-secret <secret>\n"
            ))
            return

        masked_key = (api_key[:4] + "****" + api_key[-2:]) if len(api_key) > 6 else "****"
        self.stdout.write(self.style.MIGRATE_HEADING(
            f"\n--- Cloudinary Food Image Migration & Verification ---\n"
            f"Cloud Name: {cloud_name}\n"
            f"API Key:    {masked_key}\n"
        ))

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

        results = []
        uploaded_count = 0
        skipped_count = 0
        verified_count = 0
        db_updated_count = 0

        self.stdout.write(f"Processing {len(MENU_ITEMS_MAPPING)} menu items...\n")

        for item_info in MENU_ITEMS_MAPPING:
            item_id = item_info["id"]
            dish_name = item_info["name"]
            filename = item_info["image_file"]
            img_path = media_dir / filename
            stem = Path(filename).stem

            # Public ID in Cloudinary: media/menu_items/<stem>
            target_public_id = f"media/menu_items/{stem}"
            db_relpath = f"menu_items/{filename}"
            delivery_url = f"https://res.cloudinary.com/{cloud_name}/image/upload/v1/media/{db_relpath}"

            status_str = "PENDING"

            if not img_path.exists():
                self.stderr.write(self.style.ERROR(f"[-] Missing local binary for #{item_id} {dish_name}: {img_path}"))
                results.append((item_id, dish_name, filename, "Local file missing", "No"))
                continue

            # Step 1: Check existing status on Cloudinary
            exists_on_cloud, content_type = self.check_asset_exists(delivery_url)

            if verify_only:
                if exists_on_cloud:
                    status_str = f"200 OK ({content_type})"
                    verified_count += 1
                else:
                    status_str = f"{content_type}"
            else:
                # Step 2: Upload if missing or forced
                if exists_on_cloud and not force:
                    self.stdout.write(f"  [#{item_id:2d}] {dish_name:<22} -> Already on Cloudinary ({content_type}). Skipping re-upload.")
                    status_str = f"Existing ({content_type})"
                    skipped_count += 1
                else:
                    self.stdout.write(f"  [#{item_id:2d}] {dish_name:<22} -> Uploading to Cloudinary ({target_public_id}) ... ", ending="")
                    try:
                        res = cloudinary.uploader.upload(
                            str(img_path),
                            public_id=target_public_id,
                            overwrite=True,
                            resource_type="image",
                        )
                        self.stdout.write(self.style.SUCCESS("OK!"))
                        uploaded_count += 1

                        # Re-verify URL
                        v_ok, v_type = self.check_asset_exists(delivery_url)
                        if v_ok:
                            status_str = f"Uploaded ({v_type})"
                            verified_count += 1
                        else:
                            status_str = f"Uploaded ({v_type})"
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"FAILED ({e})"))
                        status_str = f"Upload failed: {e}"

            # Step 3: Link PostgreSQL MenuItem database record
            db_status = "No change"
            matching_item = None
            try:
                matching_item = MenuItem.objects.filter(id=item_id).first()
                if not matching_item:
                    matching_item = MenuItem.objects.filter(name__iexact=dish_name).first()

                if matching_item:
                    if str(matching_item.image) != db_relpath:
                        matching_item.image = db_relpath
                        matching_item.save(update_fields=['image'])
                        db_status = f"Linked to #{matching_item.id}"
                        db_updated_count += 1
                    else:
                        db_status = f"Already linked (#{matching_item.id})"
                else:
                    db_status = "Item not found in DB"
            except Exception as e:
                db_status = f"DB error: {e}"

            results.append((item_id, dish_name, filename, status_str, db_status))

        # Print final formatted summary table
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(f"{'ID':<4} {'Dish Name':<24} {'Status on Cloudinary':<24} {'Database Link'}")
        self.stdout.write("-" * 80)
        for r_id, r_name, r_file, r_status, r_db in results:
            self.stdout.write(f"{r_id:<4} {r_name:<24} {r_status:<24} {r_db}")
        self.stdout.write("=" * 80)
        self.stdout.write(self.style.SUCCESS(
            f"\nSummary:\n"
            f"  Uploaded to Cloudinary: {uploaded_count}\n"
            f"  Skipped (already on Cloudinary): {skipped_count}\n"
            f"  Database records updated: {db_updated_count}\n"
            f"  Live assets verified reachable: {verified_count}\n"
        ))
