from django.core.management.base import BaseCommand
from apps.links.models import ShortURL


class Command(BaseCommand):
    help = "Seed the database with a large number of ShortURL records"

    def add_arguments(self, parser):
        parser.add_argument(
            "--count",
            type=int,
            default=100_000,
            help="Number of ShortURL records to create",
        )

    def handle(self, *args, **options):
        count = options["count"]

        self.stdout.write(
            self.style.WARNING(
                f"Creating {count:,} ShortURL records..."
            )
        )

        batch_size = 1000
        objects = []

        for i in range(1, count + 1):
            objects.append(
                ShortURL(
                    short_code=f"bench{i:07d}",
                    original_url=f"https://example.com/page/{i}",
                    is_active=True,
                )
            )

            if len(objects) >= batch_size:
                ShortURL.objects.bulk_create(
                    objects,
                    batch_size=batch_size,
                    ignore_conflicts=True,
                )
                objects = []

                if i % 10_000 == 0:
                    self.stdout.write(
                        f"Created approximately {i:,} records..."
                    )

        if objects:
            ShortURL.objects.bulk_create(
                objects,
                batch_size=batch_size,
                ignore_conflicts=True,
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Finished seeding {count:,} ShortURL records."
            )
        )