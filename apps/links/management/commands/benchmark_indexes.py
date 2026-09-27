from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import connection

from apps.links.models import ShortURL


User = get_user_model()


class Command(BaseCommand):
    help = (
        "Executes EXPLAIN (ANALYZE, BUFFERS) comparisons "
        "to illustrate query plan behaviors."
    )

    def _execute_and_print_plan(
        self,
        title: str,
        query: str,
        params: tuple,
    ):
        self.stdout.write(
            self.style.MIGRATE_HEADING(
                f"\n{'=' * 80}"
            )
        )

        self.stdout.write(
            self.style.MIGRATE_HEADING(
                f"SCENARIO: {title}"
            )
        )

        self.stdout.write(
            self.style.MIGRATE_HEADING(
                f"{'=' * 80}"
            )
        )

        with connection.cursor() as cursor:
            cursor.execute(
                f"EXPLAIN (ANALYZE, BUFFERS) {query}",
                params,
            )

            rows = cursor.fetchall()

            for row in rows:
                line = row[0]

                if "Seq Scan" in line:
                    self.stdout.write(
                        self.style.ERROR(f"  {line}")
                    )

                elif (
                    "Index Scan" in line
                    or "Index Only Scan" in line
                ):
                    self.stdout.write(
                        self.style.SUCCESS(f"  {line}")
                    )

                elif "Sort" in line:
                    self.stdout.write(
                        self.style.WARNING(f"  {line}")
                    )

                else:
                    self.stdout.write(f"  {line}")

    def handle(self, *args, **options):

        # ---------------------------------------------------------
        # Get a sample ShortURL
        # ---------------------------------------------------------

        target_link = ShortURL.objects.first()

        if not target_link:
            self.stdout.write(
                self.style.ERROR(
                    "No ShortURL records found. "
                    "Run: python manage.py seed_urls --count 100000"
                )
            )
            return

        # ---------------------------------------------------------
        # Get benchmark user
        # ---------------------------------------------------------

        power_user = User.objects.filter(
            email="benchmark@example.com"
        ).first()

        if not power_user:
            self.stdout.write(
                self.style.ERROR(
                    "Benchmark user missing. "
                    "Create benchmark@example.com first."
                )
            )
            return

        self.stdout.write(
            self.style.SUCCESS(
                f"Benchmark user ID: {power_user.id}"
            )
        )

        # ---------------------------------------------------------
        # Scenario 1
        # Unindexed original_url lookup
        # ---------------------------------------------------------

        self._execute_and_print_plan(
            title=(
                "Unindexed Filter: "
                "Lookup by original_url"
            ),
            query=(
                "SELECT id, short_code, original_url "
                "FROM links_shorturl "
                "WHERE original_url = %s"
            ),
            params=(target_link.original_url,),
        )

        # ---------------------------------------------------------
        # Scenario 2
        # Indexed short_code lookup
        # ---------------------------------------------------------

        self._execute_and_print_plan(
            title=(
                "Indexed Unique Filter: "
                "Lookup by short_code"
            ),
            query=(
                "SELECT original_url, is_active, expires_at "
                "FROM links_shorturl "
                "WHERE short_code = %s"
            ),
            params=(target_link.short_code,),
        )

        # ---------------------------------------------------------
        # Scenario 3
        # Composite index
        #
        # Index:
        # (owner_id, created_at DESC)
        # ---------------------------------------------------------

        self._execute_and_print_plan(
            title=(
                "Composite Index Filter + Ordering: "
                "owner_id + created_at DESC"
            ),
            query=(
                "SELECT id, short_code, original_url, created_at "
                "FROM links_shorturl "
                "WHERE owner_id = %s "
                "ORDER BY created_at DESC "
                "LIMIT 20"
            ),
            params=(power_user.id,),
        )

        # ---------------------------------------------------------
        # Scenario 4
        # Leftmost-prefix violation
        #
        # The composite index starts with owner_id.
        # We don't filter by owner_id here.
        # ---------------------------------------------------------

        self._execute_and_print_plan(
            title=(
                "Violating Leftmost Prefix: "
                "ORDER BY created_at DESC without owner_id"
            ),
            query=(
                "SELECT id, short_code, original_url, created_at "
                "FROM links_shorturl "
                "ORDER BY created_at DESC "
                "LIMIT 20"
            ),
            params=(),
        )

        self.stdout.write(
            self.style.SUCCESS(
                "\nIndex benchmark completed successfully."
            )
        )