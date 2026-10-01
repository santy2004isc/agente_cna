from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from ...models import RegistroFalloAPI
from .user import admin_required


@login_required
@admin_required
def registros_fallos_api_view(request):
    """
    Auditoría y consulta de registros de fallos de API y conmutación fallback (RF-3.3, RNF-04).
    """
    fallos = RegistroFalloAPI.objects.select_related('usuario', 'mensaje').order_by('-fecha_evento')
    
    # Filtro opcional por proveedor
    proveedor_filtro = request.GET.get('proveedor')
    if proveedor_filtro in ['GROQ', 'GEMINI']:
        fallos = fallos.filter(proveedor_solicitado=proveedor_filtro)

    context = {
        'fallos': fallos,
        'proveedor_filtro': proveedor_filtro,
        'total_fallos': fallos.count(),
    }
    return render(request, 'admin/fallos_api.html', context)