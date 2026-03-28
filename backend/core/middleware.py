"""Runtime-only FURATIC middleware for bans and After Hours gating."""
from django.http import HttpResponse
from django.shortcuts import redirect

from core import site_mode, user_manager


_BAN_ALWAYS_ALLOWED_PREFIXES = (
    "/static/",
    "/favicon.ico",
)

_MODERATOR_RECOVERY_PREFIXES = (
    "/admin/",
    "/moderator/",
    "/api/moderator/",
    "/accounts/",
    "/login/",
    "/logout/",
    "/logged-in/",
)

_ALLOWED_PREFIXES = (
    "/afterhours/",
    "/admin/",
    "/moderator/",
    "/api/moderator/",
    "/api/site-mode/",
    "/accounts/",
    "/login/",
    "/logout/",
    "/logged-in/",
    "/static/",
    "/favicon.ico",
)


class ClientIpBanMiddleware:
    """Resolve the real client IP and block banned traffic."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.client_ip = user_manager.get_client_ip(request)
        path = request.path

        if request.client_ip and user_manager.is_banned_ip(request.client_ip):
            if path.startswith(_BAN_ALWAYS_ALLOWED_PREFIXES):
                return self.get_response(request)
            if path.startswith(_MODERATOR_RECOVERY_PREFIXES) and user_manager.can_moderate(
                getattr(request, "user", None)
            ):
                return self.get_response(request)
            return HttpResponse("This IP address is banned.", status=403)

        return self.get_response(request)


class AfterHoursModeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path

        if site_mode.is_afterhours() and not path.startswith(_ALLOWED_PREFIXES):
            if path.startswith("/ajax/") or path.startswith("/api/"):
                return HttpResponse(
                    "FURATIC is currently in After Hours mode.",
                    status=503,
                )
            return redirect("afterhours")

        return self.get_response(request)
