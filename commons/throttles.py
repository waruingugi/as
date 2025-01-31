from rest_framework.throttling import SimpleRateThrottle


class AuthenticationThrottle(SimpleRateThrottle):
    scope = "authentication_throttle"

    def get_cache_key(self, request, view):
        return self.get_ident(request)
