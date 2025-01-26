# from datetime import timedelta

# from django.core.cache import cache
# from django.utils.timezone import now
# from sortedcontainers import SortedList

# from analytics.constants import CrashesToMonitor
# from commons.constants import CacheKeys
# from commons.logger import logger
# from observers.models import Multiplier


# def cache_crash_intervals(crash=CrashesToMonitor.OVER_20X.value):
#     for crash in CrashesToMonitor.list():
#         logger.info(f"Calculating {crash} intervals.")
#         three_days_ago = now() - timedelta(days=3)
#         crashes = list(
#             Multiplier.objects.filter(crash__gte=crash, created_at__gte=three_days_ago)
#             .order_by("created_at")
#             .values_list("created_at", flat=True)
#         )

#         # Recalculate intervals in seconds
#         intervals = [
#             (crashes[i] - crashes[i - 1]).total_seconds()
#             for i in range(1, len(crashes))
#         ]

#         # Save the recalculated sorted list to cache
#         sorted_list = SortedList(intervals)

#         cache_key = CacheKeys.CRASH_INTERVALS.format(crash)
#         cache.set(cache_key, sorted_list)
#         logger.info(f"Saved {crash} intervals to cache.")
