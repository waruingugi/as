# from django.core.cache import cache
# from rest_framework.response import Response
# from rest_framework.views import APIView

# from commons.constants import CacheKeys, SeedName
# from orchestrator.serializers import SeedSelectorSerializer


# class SeedSelectorView(APIView):
#     """
#     API endpoint to get the next seed credentials to be loaded in the workers.
#     """

#     permission_classes = []

#     def get(self, request):
#         # TODO: Implement feature to determine which seed is down here
#         serializer = SeedSelectorSerializer(data=request.query_params)
#         serializer.is_valid(raise_exception=True)

#         # Get the validated app name
#         app_name = serializer.validated_data["app"]

#         # Cache key for the specific app
#         cache_key = CacheKeys.SEED_SELECTOR.format(app_name)

#         # Get the current request count from the cache (default to 0 if not set)
#         current_request_count = cache.get(cache_key, 0)

#         # Increment the counter and store it back in the cache
#         current_request_count += 1
#         cache.set(cache_key, current_request_count, timeout=60 * 60 * 24 * 365)

#         # Calculate the next seed index
#         seed_index = (current_request_count - 1) % len(SeedName.list())
#         next_seed = SeedName.list()[seed_index]

#         # Return the seed value
#         return Response({"seed": next_seed})
