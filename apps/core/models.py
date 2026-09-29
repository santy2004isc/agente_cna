import uuid
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from pgvector.django import VectorField


# -----------------------------------------------------------------------------
# 1. USUARIOS Y AUTENTICACIÓN
# -----------------------------------------------------------------------------
class AdministradorUsuarios(BaseUserManager):
    def create_user(self, correo_electronico, password=None, **extra_fields):
        if not correo_electronico:
            raise ValueError('El correo electrónico es obligatorio.')
        correo_electronico = self.normalize_email(correo_electronico)
        user = self.model(correo_electronico=correo_electronico, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, correo_electronico, password=None, **extra_fields):
        extra_fields.setdefault('rol', 'administrador')
        extra_fields.setdefault('es_staff', True)
        extra_fields.setdefault('es_superuser', True)
        return self.create_user(correo_electronico, password, **extra_fields)


class Usuario(AbstractBaseUser, PermissionsMixin):
    ROLES = (
        ('administrador', 'Administrador'),
        ('gestor_conocimiento', 'Gestor de la Base de Conocimiento'),
        ('usuario_registrado', 'Usuario Registrado'),
    )

    id_identificador = models.CharField(
        max_length=30, 
        unique=True, 
        verbose_name='ID Identificador'
    )
    correo_electronico = models.EmailField(
        max_length=254, 
        unique=True, 
        verbose_name='Correo Electrónico'
    )
    nombre = models.CharField(max_length=100, verbose_name='Nombre')
    apellidos = models.CharField(max_length=100, verbose_name='Apellidos')
    rol = models.CharField(
        max_length=30, 
        choices=ROLES, 
        default='usuario_registrado', 
        verbose_name='Rol'
    )
    es_activo = models.BooleanField(default=True, verbose_name='Está Activo')
    es_staff = models.BooleanField(default=False, verbose_name='Acceso al Admin')
    fecha_registro = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de Registro')
    ultima_conexion = models.DateTimeField(null=True, blank=True, verbose_name='Última Conexión')

    objects = AdministradorUsuarios()

    USERNAME_FIELD = 'correo_electronico'
    REQUIRED_FIELDS = ['nombre', 'apellidos']

    class Meta:
        db_table = 'usuarios'
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'

    def __str__(self):
        return f"{self.id_identificador} - {self.correo_electronico}"


# -----------------------------------------------------------------------------
# 2. DOCUMENTOS Y EMBEDDINGS (RAG)
# -----------------------------------------------------------------------------
class DocumentoLegal(models.Model):
    ESTADOS = (
        ('pendiente', 'Pendiente'),
        ('procesando', 'Procesando'),
        ('completado', 'Completado'),
        ('error', 'Error de Procesamiento'),
    )

    titulo = models.CharField(max_length=255, verbose_name='Título de la Ley')
    nombre_archivo_original = models.CharField(max_length=255, verbose_name='Nombre Archivo Original')
    archivo_pdf = models.FileField(upload_to='leyes_pdf/', verbose_name='Archivo PDF')
    es_ley_federal_valida = models.BooleanField(default=True, verbose_name='Es Ley Federal Válida')
    estado_procesamiento = models.CharField(
        max_length=30, 
        choices=ESTADOS, 
        default='pendiente', 
        verbose_name='Estado'
    )
    total_fragmentos = models.IntegerField(default=0, verbose_name='Total de Fragmentos')
    cargado_por = models.ForeignKey(
        Usuario, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='documentos_cargados',
        verbose_name='Cargado por'
    )
    fecha_carga = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de Carga')
    fecha_actualizacion = models.DateTimeField(auto_now=True, verbose_name='Fecha de Actualización')

    class Meta:
        db_table = 'documentos_legales'
        verbose_name = 'Documento Legal'
        verbose_name_plural = 'Documentos Legales'

    def __str__(self):
        return self.titulo


class FragmentoDocumento(models.Model):
    documento = models.ForeignKey(
        DocumentoLegal, 
        on_delete=models.CASCADE, 
        related_name='fragmentos',
        verbose_name='Documento Legal'
    )
    indice_fragmento = models.IntegerField(verbose_name='Índice del Fragmento')
    contenido_texto = models.TextField(verbose_name='Contenido del Texto')
    numero_articulo = models.CharField(
        max_length=100, 
        null=True, 
        blank=True, 
        verbose_name='Número de Artículo'
    )
    numero_pagina = models.IntegerField(null=True, blank=True, verbose_name='Número de Página')
    vector_embedding = VectorField(dimensions=1536, verbose_name='Vector Embedding')
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de Creación')

    class Meta:
        db_table = 'fragmentos_documentos'
        verbose_name = 'Fragmento de Documento'
        verbose_name_plural = 'Fragmentos de Documentos'

    def __str__(self):
        return f"{self.documento.titulo} - Frag #{self.indice_fragmento}"


# -----------------------------------------------------------------------------
# 3. CONVERSACIONES Y HISTORIAL
# -----------------------------------------------------------------------------
class Conversacion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    usuario = models.ForeignKey(
        Usuario, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        related_name='conversaciones',
        verbose_name='Usuario'
    )
    identificador_invitado = models.CharField(
        max_length=100, 
        null=True, 
        blank=True, 
        verbose_name='ID de Invitado'
    )
    titulo = models.CharField(max_length=255, default='Nueva consulta', verbose_name='Título')
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de Creación')
    fecha_actualizacion = models.DateTimeField(auto_now=True, verbose_name='Fecha de Actualización')

    class Meta:
        db_table = 'conversaciones'
        verbose_name = 'Conversación'
        verbose_name_plural = 'Conversaciones'

    def __str__(self):
        return f"{self.titulo} - {self.id}"


class Mensaje(models.Model):
    EMISORES = (
        ('usuario', 'Usuario'),
        ('asistente', 'Asistente IA'),
        ('sistema', 'Sistema'),
    )

    conversacion = models.ForeignKey(
        Conversacion, 
        on_delete=models.CASCADE, 
        related_name='mensajes',
        verbose_name='Conversación'
    )
    emisor = models.CharField(max_length=20, choices=EMISORES, verbose_name='Emisor')
    contenido_texto = models.TextField(verbose_name='Contenido del Mensaje')
    citas_legales = models.JSONField(default=list, blank=True, verbose_name='Citas Legales')
    fue_rechazado_por_guardrail = models.BooleanField(
        default=False, 
        verbose_name='Rechazado por Guardrail'
    )
    tiempo_respuesta_ms = models.IntegerField(
        null=True, 
        blank=True, 
        verbose_name='Tiempo de Respuesta (ms)'
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de Emisión')

    class Meta:
        db_table = 'mensajes'
        verbose_name = 'Mensaje'
        verbose_name_plural = 'Mensajes'

    def __str__(self):
        return f"[{self.emisor}] {self.contenido_texto[:30]}..."


# -----------------------------------------------------------------------------
# 4. CUOTAS Y CONTROL DE LÍMITES
# -----------------------------------------------------------------------------
class CuotaUsuario(models.Model):
    usuario = models.OneToOneField(
        Usuario, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        related_name='cuota',
        verbose_name='Usuario'
    )
    identificador_invitado = models.CharField(
        max_length=100, 
        unique=True, 
        null=True, 
        blank=True, 
        verbose_name='ID Invitado'
    )
    limite_diario_mensajes = models.IntegerField(default=10, verbose_name='Límite Diario')
    mensajes_consumidos_hoy = models.IntegerField(default=0, verbose_name='Mensajes Consumidos Hoy')
    fecha_ultimo_reinicio = models.DateField(auto_now=True, verbose_name='Último Reinicio')

    class Meta:
        db_table = 'cuotas_usuarios'
        verbose_name = 'Cuota de Usuario'
        verbose_name_plural = 'Cuotas de Usuarios'

    def __str__(self):
        return f"Cuota: {self.mensajes_consumidos_hoy}/{self.limite_diario_mensajes}"