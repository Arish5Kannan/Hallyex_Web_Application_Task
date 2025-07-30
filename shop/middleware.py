from django.utils.deprecation import MiddlewareMixin
from .models import CustomUser

class ImpersonateMiddleware(MiddlewareMixin):
    def process_request(self, request):
        impersonate_id = request.session.get('impersonate_id')
        if impersonate_id:
            try:
                user = CustomUser.objects.get(id=impersonate_id)
                request.impersonating = True
                request.user = user
            except CustomUser.DoesNotExist:
                del request.session['impersonate_id']
        else:
            request.impersonating = False
