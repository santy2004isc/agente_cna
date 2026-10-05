import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db import transaction
from django.contrib import messages

from ...models import Usuario, Conversacion, Mensaje
from ...decorators import roles_requeridos
from ...services.chat_service import buscar_contexto_normativo, generar_respuesta_ia_con_fallback


@login_required
@roles_requeridos(Usuario.Rol.GESTOR, Usuario.Rol.ADMINISTRADOR)
def chat_gestor_interfaz_view(request, conversacion_id=None):
    usuario = request.user
    conversaciones = Conversacion.objects.filter(usuario=usuario).order_by('-fecha_creacion')
    
    conversacion_actual = None
    mensajes = []

    if conversacion_id:
        conversacion_actual = get_object_or_404(Conversacion, id=conversacion_id, usuario=usuario)
    elif conversaciones.exists():
        conversacion_actual = conversaciones.first()

    if conversacion_actual:
        mensajes = conversacion_actual.mensajes.all().order_by('fecha_envio')

    context = {
        'conversaciones': conversaciones,
        'conversacion_actual': conversacion_actual,
        'mensajes': mensajes,
        'mensajes_restantes': "Ilimitado"
    }
    return render(request, 'gestor/chat.html', context)


@login_required
@roles_requeridos(Usuario.Rol.GESTOR, Usuario.Rol.ADMINISTRADOR)
@require_POST
def crear_nueva_conversacion_gestor_view(request):
    nueva_conv = Conversacion.objects.create(
        usuario=request.user,
        titulo="Consulta Normativa (Gestor)"
    )
    return redirect('gestor_chat_conversacion', conversacion_id=nueva_conv.id)


@login_required
@roles_requeridos(Usuario.Rol.GESTOR, Usuario.Rol.ADMINISTRADOR)
@require_POST
def eliminar_conversacion_gestor_view(request, conversacion_id):
    conv = get_object_or_404(Conversacion, id=conversacion_id, usuario=request.user)
    conv.delete()
    messages.success(request, "La conversación fue eliminada.")
    return redirect('gestor_chat_interfaz')


@login_required
@roles_requeridos(Usuario.Rol.GESTOR, Usuario.Rol.ADMINISTRADOR)
@require_POST
def enviar_mensaje_gestor_api_view(request):
    usuario = request.user

    try:
        data = json.loads(request.body)
        pregunta = data.get('mensaje', '').strip()
        conversacion_id = data.get('conversacion_id')

        if not pregunta:
            return JsonResponse({'error': 'El mensaje no puede estar vacío.'}, status=400)

        if conversacion_id:
            conversacion = get_object_or_404(Conversacion, id=conversacion_id, usuario=usuario)
        else:
            titulo_auto = pregunta[:40] + ("..." if len(pregunta) > 40 else "")
            conversacion = Conversacion.objects.create(usuario=usuario, titulo=titulo_auto)

        if conversacion.mensajes.count() == 0 and conversacion.titulo == "Consulta Normativa (Gestor)":
            conversacion.titulo = pregunta[:40] + ("..." if len(pregunta) > 40 else "")
            conversacion.save()

        with transaction.atomic():
            msg_usuario = Mensaje.objects.create(
                conversacion=conversacion,
                emisor=Mensaje.Emisor.USUARIO,
                contenido_texto=pregunta
            )

            contexto, citas = buscar_contexto_normativo(pregunta)
            respuesta_texto, proveedor_usado, conmutado = generar_respuesta_ia_con_fallback(
                pregunta_usuario=pregunta,
                contexto_normativo=contexto,
                usuario=usuario
            )

            msg_sistema = Mensaje.objects.create(
                conversacion=conversacion,
                emisor=Mensaje.Emisor.SISTEMA,
                contenido_texto=respuesta_texto,
                proveedor_ia=proveedor_usado,
                conmutado_fallback=conmutado,
                citas=citas
            )

        return JsonResponse({
            'ok': True,
            'conversacion_id': str(conversacion.id),
            'conversacion_titulo': conversacion.titulo,
            'mensajes_restantes': "Ilimitado",
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