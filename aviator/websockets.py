from analytics.routes.websockets import analytics_url_patterns
from observers.routes.websockets import multipliers_url_patterns

# Combine all WebSocket routes
websocket_urlpatterns = [
    *analytics_url_patterns,
    *multipliers_url_patterns,
]
