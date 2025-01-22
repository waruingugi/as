# from django.core.cache import cache
# from django.urls import reverse
# from rest_framework import status
# from rest_framework.test import APIClient, APITestCase

# from commons.constants import BettingApps, CacheKeys, SeedNames


# class SeedSelectorAPITest(APITestCase):
#     def setUp(self):
#         self.client = APIClient()

#         self.url = reverse(
#             "orchestrator:seed-selector"
#         )  # Ensure the URL name matches your `urls.py`
#         self.betting_app = (
#             BettingApps.BETIKA.value
#         )  # Replace with the appropriate value from `BettingApps`

#         # Seed values for verification
#         self.seed_values = SeedNames.list()

#     def tearDown(self):
#         # Clear the cache after each test
#         cache.clear()

#     def test_valid_app_returns_seed(self) -> None:
#         """
#         Ensure the API returns the correct seed value for a valid app.
#         """
#         for i in range(1, 5):  # Loop through 4 requests
#             response = self.client.get(self.url, {"app": self.betting_app})
#             self.assertEqual(response.status_code, status.HTTP_200_OK)
#             # Verify the seed value matches the expected cyclic value
#             expected_seed = self.seed_values[(i - 1) % len(self.seed_values)]
#             self.assertEqual(response.json(), {"seed": expected_seed})

#     def test_invalid_app_returns_error(self) -> None:
#         """
#         Ensure the API returns an error for an invalid app name.
#         """
#         response = self.client.get(self.url, {"app": "INVALID_APP"})
#         self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
#         self.assertIn("app", response.json())

#     def test_missing_app_returns_error(self) -> None:
#         """
#         Ensure the API returns an error if the 'app' parameter is missing.
#         """
#         response = self.client.get(self.url)
#         self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
#         self.assertIn("app", response.json())

#     def test_cache_persistence(self) -> None:
#         """
#         Ensure the cache tracks the request count correctly across multiple requests.
#         """
#         for i in range(1, 4):  # Make 3 requests
#             self.client.get(self.url, {"app": self.betting_app})

#         # Verify the cached value matches the total requests
#         cache_key = CacheKeys.SEED_SELECTOR.format(self.betting_app)
#         cached_count = cache.get(cache_key)
#         self.assertEqual(cached_count, 3)

#     def test_cache_expiration(self) -> None:
#         """
#         Ensure the cache value persists for the configured timeout.
#         """
#         self.client.get(self.url, {"app": self.betting_app})

#         cache_key = CacheKeys.SEED_SELECTOR.format(self.betting_app)
#         self.assertIsNotNone(cache.get(cache_key))
