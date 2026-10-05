from functools import wraps
from django.core.exceptions import PermissionDenied

def roles_requeridos(*roles_permitidos):
    """
    Verifica que el usuario autenticado posea uno de los roles autorizados.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if request.user.is_authenticated and request.user.rol in roles_permitidos:
                return view_func(request, *args, **kwargs)
            raise PermissionDenied
        return _wrapped_view
    return decorator