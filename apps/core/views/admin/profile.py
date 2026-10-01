from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from ...forms.profile_forms import EditarPerfilForm
from .user import admin_required


@login_required
@admin_required
def perfil_admin_view(request):
    user = request.user
    if request.method == 'POST':
        form = EditarPerfilForm(request.POST, instance=user, user=user)
        if form.is_valid():
            form.save()
            messages.success(request, "Perfil actualizado exitosamente.")
            return redirect('admin_perfil')
    else:
        form = EditarPerfilForm(instance=user, user=user)

    return render(request, 'admin/perfil.html', {'form': form})