from django.urls import path
from .views.auth import autenticacion, router
from .views.admin import api_log, profile, user
from .views.gestor import gestor_views

urlpatterns = [
    path('', router.home_router_view, name='router'),
    path('login/', autenticacion.login_view, name='login'),
    path('logout/', autenticacion.logout_view, name='logout'),
    path('registro/', autenticacion.registro_view, name='registro'),

    # Administrador
    path('admin-panel/', user.admin_dashboard_view, name='admin_dashboard'),
    path('admin-panel/usuarios/crear/', user.crear_usuario_view, name='admin_crear_usuario'),
    path('admin-panel/usuarios/<int:user_id>/editar/', user.editar_usuario_view, name='admin_editar_usuario'),
    path('admin-panel/usuarios/<int:user_id>/estado/', user.cambiar_estado_usuario_view, name='admin_cambiar_estado'),
    path('admin-panel/usuarios/<int:user_id>/eliminar/', user.eliminar_usuario_view, name='admin_eliminar_usuario'),
    path('admin-panel/perfil/', profile.perfil_admin_view, name='admin_perfil'),
    path('admin-panel/fallos-api/', api_log.registros_fallos_api_view, name='admin_fallos_api'),

    # Gestor
    path('gestor-panel/', gestor_views.gestor_dashboard_view, name='gestor_dashboard'),
    path('gestor-panel/documentos/cargar/', gestor_views.cargar_documento_view, name='gestor_cargar_documento'),
    path('gestor-panel/documentos/<int:ley_id>/editar/', gestor_views.editar_ley_view, name='gestor_editar_ley'),
    path('gestor-panel/perfil/', gestor_views.perfil_gestor_view, name='gestor_perfil'),

]