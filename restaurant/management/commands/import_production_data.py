from pathlib import Path

from django.core.management import BaseCommand, call_command


class Command(BaseCommand):
    help = "Import restaurant fixture data once"

    def handle(self, *args, **options):
        fixture_path = Path("restaurant_data.json")

        if not fixture_path.exists():
            self.stderr.write(
                self.style.ERROR("restaurant_data.json not found.")
            )
            return

        self.stdout.write("Importing restaurant data...")

        call_command("loaddata", str(fixture_path))

        self.stdout.write(
            self.style.SUCCESS("Restaurant data imported successfully.")
        )
