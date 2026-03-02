from django.utils.deprecation import MiddlewareMixin
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework.exceptions import AuthenticationFailed
from user.func import ensure_user_balances, set_user_info_to_redis


class RedisUserMiddleware(MiddlewareMixin):
    def process_request(self, request):
        try:
            auth = JWTAuthentication().authenticate(request)
            if auth:
                request.user, _ = auth
                set_user_info_to_redis(user=request.user)
        except (InvalidToken, TokenError, AuthenticationFailed):
            pass


class RedisBalanceMiddleware(MiddlewareMixin):
    def process_view(self, request, view_func, view_args, view_kwargs):
        user = getattr(request, 'user', None)
        if not user or not user.is_authenticated:
            return None

        ensure_user_balances(user)
