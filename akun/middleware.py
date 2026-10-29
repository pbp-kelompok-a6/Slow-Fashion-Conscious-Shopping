from .models import Profile


class EnsureProfileMiddleware:
    """Repair legacy accounts when authenticated, without a data migration."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            Profile.objects.get_or_create(user=request.user)
        return self.get_response(request)
