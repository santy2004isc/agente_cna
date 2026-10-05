import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db import transaction
from django.contrib import messages

from ...models import Usuario, Conversacion, Mensaje, RegistroFalloAPI
from ...forms.usuario_forms import EditarPerfilUsuarioForm
from ...services.chat_service import buscar_contexto_normativo, generar_respuesta_ia_con_fallback


@login_required
def chat_interfaz_view(request, conversacion_id=None):
    """
    Interfaz principal del chat para el Usuario Registrado.
    """
    conversaciones = Conversacion.objects.filter(usuario=request.user)
    conversacion_actual = None
    mensajes = []

    if conversacion_id:
        conversacion_actual = get_object_or_404(Conversacion, id=conversacion_id, usuario=request.user)
        mensajes = conversacion_actual.mensajes.all()
    elif conversaciones.exists():
        conversacion_actual = conversaciones.first()
        mensajes = conversacion_actual.mensajes.all()

    # Cálculo de mensajes restantes
    mensajes_restantes = max(0, request.user.cuota_diaria_mensajes - request.user.mensajes_usados_hoy)

    context = {
        'conversaciones': conversaciones,
        'conversacion_actual': conversacion_actual,
        'mensajes': mensajes,
        'mensajes_restantes': mensajes_restantes,
    }
    return render(request, 'usuario/chat.html', context)


@login_required
@require_POST
def crear_nueva_conversacion_view(request):
    """
    Crea un nuevo hilo/contenedor de conversación.
    """
    nueva_conv = Conversacion.objects.create(
        usuario=request.user,
        titulo="Consulta Normativa"
    )
    return redirect('chat_conversacion', conversacion_id=nueva_conv.id)


@login_required
@require_POST
def eliminar_conversacion_view(request, conversacion_id):
    """
    Elimina una conversación y sus mensajes asociados (ON DELETE CASCADE).
    """
    conv = get_object_or_404(Conversacion, id=conversacion_id, usuario=request.user)
    conv.delete()
    messages.success(request, "La conversación fue eliminada.")
    return redirect('chat_interfaz')


@login_required
@require_POST
def enviar_mensaje_api_view(request):
    """
    Endpoint AJAX: Valida cuota, guarda mensaje, ejecuta RAG con fallback y acumula cuota.
    """
    usuario = request.user

    # 1. Validar Cuota Diaria
    if usuario.mensajes_usados_hoy >= usuario.cuota_diaria_mensajes:
        return JsonResponse({
            'error': f'Ha alcanzado el límite diario de su cuota ({usuario.cuota_diaria_mensajes} mensajes).'
        }, status=429)

    try:
        data = json.loads(request.body)
        pregunta = data.get('mensaje', '').strip()
        conversacion_id = data.get('conversacion_id')

        if not pregunta:
            return JsonResponse({'error': 'El mensaje no puede estar vacío.'}, status=400)

        # 2. Obtener o Crear Hilo de Conversación
        if conversacion_id:
            conversacion = get_object_or_404(Conversacion, id=conversacion_id, usuario=usuario)
        else:
            titulo_auto = pregunta[:40] + ("..." if len(pregunta) > 40 else "")
            conversacion = Conversacion.objects.create(usuario=usuario, titulo=titulo_auto)

        # Actualizar título por defecto si es el primer mensaje
        if conversacion.mensajes.count() == 0 and conversacion.titulo == "Consulta Normativa":
            conversacion.titulo = pregunta[:40] + ("..." if len(pregunta) > 40 else "")
            conversacion.save()

        with transaction.atomic():
            # 3. Guardar Mensaje del Usuario
            msg_usuario = Mensaje.objects.create(
                conversacion=conversacion,
                emisor=Mensaje.Emisor.USUARIO,
                contenido_texto=pregunta
            )

            # 4. Búsqueda RAG y Generación con IA / Fallback
            contexto, citas = buscar_contexto_normativo(pregunta)
            respuesta_texto, proveedor_usado, conmutado = generar_respuesta_ia_con_fallback(pregunta_usuario=pregunta, contexto_normativo=contexto, usuario=usuario)

            # 5. Guardar Respuesta del Sistema
            msg_sistema = Mensaje.objects.create(
                conversacion=conversacion,
                emisor=Mensaje.Emisor.SISTEMA,
                contenido_texto=respuesta_texto,
                proveedor_ia=proveedor_usado,
                conmutado_fallback=conmutado,
                citas=citas
            )

            # 6. Registrar Auditoría si hubo Fallback / Conmutación
            if conmutado:
                RegistroFalloAPI.objects.create(
                    usuario=usuario,
                    mensaje=msg_sistema,
                    proveedor_solicitado=Mensaje.ProveedorIA.GROQ,
                    codigo_error="RATE_LIMIT_EXCEEDED",
                    conmutado_a=proveedor_usado,
                    exitoso=True
                )

            # 7. Incrementar consumo de la cuota diaria del usuario
            usuario.mensajes_usados_hoy += 1
            usuario.save(update_fields=['mensajes_usados_hoy'])

        mensajes_restantes = max(0, usuario.cuota_diaria_mensajes - usuario.mensajes_usados_hoy)

        return JsonResponse({
            'ok': True,
            'conversacion_id': str(conversacion.id),
            'conversacion_titulo': conversacion.titulo,
            'mensajes_restantes': mensajes_restantes,
            'pregunta': {
                'id': msg_usuario.id,
                'contenido': msg_usuario.contenido_texto,
                'fecha': msg_usuario.fecha_envio.strftime('%H:%M')
            },
            'respuesta': {
                'id': msg_sistema.id,
                'contenido': msg_sistema.contenido_texto,
                'proveedor': msg_sistema.proveedor_ia,
                'conmutado': msg_sistema.conmutado_fallback,
                'citas': citas,
                'fecha': msg_sistema.fecha_envio.strftime('%H:%M')
            }
        })

    except Exception as e:
        return JsonResponse({'error': f'Error interno: {str(e)}'}, status=500)


@login_required
def perfil_usuario_view(request):
    """
    Vista de actualización de perfil para el usuario.
    """
    user = request.user
    if request.method == 'POST':
        form = EditarPerfilUsuarioForm(request.POST, instance=user, user=user)
        if form.is_valid():
            form.save()
            messages.success(request, "Tu información de perfil ha sido actualizada.")
            return redirect('usuario_perfil')
    else:
        form = EditarPerfilUsuarioForm(instance=user, user=user)

    return render(request, 'usuario/perfil.html', {'form': form})