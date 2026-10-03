from functools import wraps
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction

from ...models import Usuario, LeyFederal, FragmentoNormativo
from ...forms.gestor_forms import CargarDocumentoForm, EditarPerfilGestorForm
from ...services.pdf_processor import (
    procesar_pdf_en_memoria,
    generar_vector_embedding,
    calcular_hash_fragmento
)


def gestor_required(view_func):
    """
    Restringe acceso a roles GESTOR o ADMINISTRADOR.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated or request.user.rol not in [Usuario.Rol.GESTOR, Usuario.Rol.ADMINISTRADOR]:
            messages.error(request, "Acceso restringido. Se requieren permisos de Gestor de la Base de Conocimiento.")
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return _wrapped_view


@login_required
@gestor_required
def gestor_dashboard_view(request):
    """
    Dashboard del Gestor: Listado de LeyFederal y total de FragmentoNormativo.
    """
    leyes = LeyFederal.objects.filter(usuario=request.user).order_by('-fecha_creacion')
    total_fragmentos = FragmentoNormativo.objects.filter(ley__usuario=request.user).count()

    context = {
        'leyes': leyes,
        'total_leyes': leyes.count(),
        'total_fragmentos': total_fragmentos,
    }
    return render(request, 'gestor/dashboard.html', context)


@login_required
@gestor_required
def cargar_documento_view(request):
    """
    Carga e ingesta de PDF -> LeyFederal y FragmentoNormativo (RF-2.1, RF-2.2, RF-2.3).
    """
    if request.method == 'POST':
        form = CargarDocumentoForm(request.POST, request.FILES)
        if form.is_valid():
            archivo_pdf = request.FILES['archivo_pdf']
            
            try:
                # 1. Procesar PDF en memoria
                hash_doc, chunks = procesar_pdf_en_memoria(archivo_pdf)

                # 2. Validación de duplicados por Hash SHA-256
                if LeyFederal.objects.filter(hash_documento=hash_doc).exists():
                    messages.error(request, "Este documento PDF ya ha sido procesado e ingresado previamente al sistema.")
                    return render(request, 'gestor/cargar_documento.html', {'form': form})

                with transaction.atomic():
                    # 3. Guardar registro principal en LeyFederal
                    ley = form.save(commit=False)
                    ley.usuario = request.user
                    ley.hash_documento = hash_doc
                    ley.save()

                    # 4. Generar vectores y guardar en FragmentoNormativo
                    fragmentos_objetos = []
                    for chunk in chunks:
                        hash_frag = calcular_hash_fragmento(chunk)
                        vector = generar_vector_embedding(chunk)
                        
                        fragmentos_objetos.append(
                            FragmentoNormativo(
                                ley=ley,
                                contenido_fragmento=chunk,
                                vector_embedding=vector,
                                hash_fragmento=hash_frag
                            )
                        )

                    FragmentoNormativo.objects.bulk_create(fragmentos_objetos)

                messages.success(request, f"La norma '{ley.nombre}' fue procesada e indexada exitosamente con {len(chunks)} fragmentos vectoriales.")
                return redirect('gestor_dashboard')

            except Exception as e:
                messages.error(request, f"Ocurrió un error al procesar el archivo: {str(e)}")
    else:
        form = CargarDocumentoForm()

    return render(request, 'gestor/cargar_documento.html', {'form': form})


@login_required
@gestor_required
def perfil_gestor_view(request):
    """
    Edición de perfil del usuario Gestor.
    """
    user = request.user
    if request.method == 'POST':
        form = EditarPerfilGestorForm(request.POST, instance=user, user=user)
        if form.is_valid():
            form.save()
            messages.success(request, "Tu perfil ha sido actualizado exitosamente.")
            return redirect('gestor_perfil')
    else:
        form = EditarPerfilGestorForm(instance=user, user=user)

    return render(request, 'gestor/perfil.html', {'form': form})