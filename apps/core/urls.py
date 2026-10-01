from django.urls import path
from .views.auth import autenticacion, router
from .views.admin import api_log, profile, user

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

]