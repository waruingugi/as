from analytics.routes.websockets import analytics_url_patterns

# Combine all WebSocket routes
websocket_urlpatterns = [
    *analytics_url_patterns,
]
