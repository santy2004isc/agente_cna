from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from ...models import Usuario


@login_required
def home_router_view(request):
    """
    Enrutador principal: Redirige al usuario a su dashboard/vista correspondiente según su rol[cite: 1, 2].
    """
    if request.user.rol == Usuario.Rol.ADMINISTRADOR:
        return redirect('admin_dashboard')
    elif request.user.rol == Usuario.Rol.GESTOR:
        return redirect('gestor_dashboard')
    else:
        return render(request, 'chat.html')
