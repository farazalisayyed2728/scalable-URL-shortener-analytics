from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List

import pytest
from django.db import connection

from apps.core.exceptions import CodeAlreadyTakenException
from apps.links.models import ShortURL
from apps.links.services.shortener import create_short_url


@pytest.mark.django_db(transaction=True)
class TestShortURLConcurrency:

    def test_concurrent_custom_code_creation_race_condition(self):
        """
        20 threads simultaneously try to create the same custom code.

        Expected:
        - 1 succeeds
        - 19 get CodeAlreadyTakenException
        - Only 1 database row exists
        """

        target_code = "faraz"
        num_threads = 20

        results: Dict[str, int] = {
            "success": 0,
            "conflict": 0,
            "other_error": 0,
        }

        def attempt_create_url(worker_id: int) -> str:

            connection.close()

            try:
                create_short_url(
                    original_url=f"https://example.com/target-{worker_id}",
                    custom_code=target_code,
                )

                return "success"

            except CodeAlreadyTakenException:
                return "conflict"

            except Exception as e:
                print(f"Unexpected worker failure: {e}")
                return "other_error"

            finally:
                connection.close()

        with ThreadPoolExecutor(max_workers=num_threads) as executor:

            futures = [
                executor.submit(attempt_create_url, i)
                for i in range(num_threads)
            ]

            for future in as_completed(futures):
                status = future.result()
                results[status] += 1

        print(f"\nConcurrency Race Results: {results}")

        assert results["success"] == 1

        assert results["conflict"] == num_threads - 1

        assert results["other_error"] == 0

        total_in_db = ShortURL.objects.filter(
            short_code=target_code
        ).count()

        assert total_in_db == 1


    def test_concurrent_random_code_generation_under_load(self):

        """
        30 threads simultaneously generate random short URLs.

        Expected:
        - 30 successful creations
        - 30 unique short codes
        """

        num_threads = 30

        allocated_codes: List[str] = []

        def attempt_random_url(worker_id: int):

            connection.close()

            try:
                link = create_short_url(
                    original_url=f"https://example.com/page-{worker_id}"
                )

                return link.short_code

            finally:
                connection.close()

        with ThreadPoolExecutor(max_workers=num_threads) as executor:

            futures = [
                executor.submit(attempt_random_url, i)
                for i in range(num_threads)
            ]

            for future in as_completed(futures):
                code = future.result()
                allocated_codes.append(code)

        assert len(allocated_codes) == num_threads

        assert len(set(allocated_codes)) == num_threads

        assert (
            ShortURL.objects
            .filter(short_code__in=allocated_codes)
            .count()
            == num_threads
        )