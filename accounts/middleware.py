from django.utils import timezone
from accounts.models import Profile

class LastActivityMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        if request.user.is_authenticated:

            activity, _ = Profile.objects.get_or_create(
                user=request.user
            )

            activity.last_activity = timezone.now()
            activity.save(update_fields=["last_activity"])

        return self.get_response(request)