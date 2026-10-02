import random
import string
from locust import HttpUser, between, task


class ShortLinkUser(HttpUser):
    """
    Simulates real-world traffic hitting the URL shortener:
    - 85% Hot Redirects (Hits Redis Cache)
    - 10% Cold Redirects (Simulates misses / non-existent keys)
    - 5% URL Creations (Exercises rate limiting and DB inserts)
    """
    # Wait between 50ms and 200ms between requests per virtual user
    wait_time = between(0.05, 0.2)

    # Pre-seeded test codes known to exist in the database/cache
    hot_codes = [f"perf_link_{i}" for i in range(1, 6)]

    def on_start(self):
        """
        Executed once per virtual user when spawned.
        Creates a set of short URLs to ensure test targets exist.
        """
        for code in self.hot_codes[:5]:
            with self.client.post(
                "/api/urls/",
                json={
                    "original_url": f"https://example.com/target/{code}",
                    "custom_code": code,
                },
                headers={"Content-Type": "application/json"},
                catch_response=True,
                name="/api/urls/ [setup]",
            ) as response:
                if response.status_code in (201, 409, 429):
                    response.success()
                else:
                    response.failure(f"Setup failed with status {response.status_code}")

    @task(85)
    def redirect_hot_cached_url(self):
        """
        Simulates high-frequency visits to popular links.
        Critical: allow_redirects=False measures OUR redirect latency,
        not the external website's loading speed.
        """
        code = random.choice(self.hot_codes)
        with self.client.get(
            f"/{code}",
            allow_redirects=False,
            catch_response=True,
            name="/{short_code} [Cache Hit / Redirect]",
        ) as response:
            # Expect HTTP 302 Found
            if response.status_code == 302:
                response.success()
            elif response.status_code == 404:
                # Accept 404 if link not yet created by setup
                response.success()
            else:
                response.failure(f"Unexpected status: {response.status_code}")

    @task(10)
    def redirect_random_cold_url(self):
        """
        Simulates visits to non-existent or rarely accessed links (exercises negative cache & DB miss).
        """
        random_suffix = "".join(random.choices(string.ascii_letters + string.digits, k=7))
        with self.client.get(
            f"/cold_{random_suffix}",
            allow_redirects=False,
            catch_response=True,
            name="/{short_code} [Cold / 404]",
        ) as response:
            if response.status_code in (404, 302):
                response.success()
            else:
                response.failure(f"Unexpected status: {response.status_code}")

    @task(5)
    def create_short_url(self):
        """
        Simulates active URL creation (exercises rate limiting, generation, and DB insertion).
        """
        rand_str = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
        payload = {
            "original_url": f"https://example.com/page/{rand_str}"
        }
        with self.client.post(
            "/api/urls/",
            json=payload,
            headers={"Content-Type": "application/json"},
            catch_response=True,
            name="/api/urls/ [Create]",
        ) as response:
            if response.status_code == 201:
                response.success()
            elif response.status_code == 429:
                # 429 is an expected outcome once the rate limit is hit!
                response.success()
            else:
                response.failure(f"Create failed with status {response.status_code}")