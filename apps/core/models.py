import uuid
from django.db import models
from django.conf import settings
from django.contrib.auth.models import AbstractUser, BaseUserManager
from pgvector.django import VectorField


# ==========================================
# 1. MÓDULO DE AUTENTICACIÓN Y USUARIOS
# ==========================================

class UserManager(BaseUserManager):
    """Manager personalizado para usar el email como credencial principal."""
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('El correo electrónico es obligatorio')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', UserRole.ADMIN)
        return self.create_user(email, password, **extra_fields)


class UserRole(models.TextChoices):
    ADMIN = 'ADMIN', 'Administrador'
    GESTOR = 'GESTOR', 'Gestor de la Base de Conocimiento'
    REGISTRADO = 'REGISTRADO', 'Usuario Registrado'


class User(AbstractUser):
    username = None  # Se elimina el nombre de usuario por defecto
    email = models.EmailField('Correo Electrónico', unique=True)
    custom_id = models.CharField('ID Personalizado', max_length=30, unique=True, editable=False)
    role = models.CharField('Rol', max_length=20, choices=UserRole.choices, default=UserRole.REGISTRADO)
    daily_message_limit = models.IntegerField('Límite de Mensajes Diarios', default=50)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    objects = UserManager()

    def save(self, *args, **kwargs):
        if not self.custom_id:
            prefix_map = {
                UserRole.ADMIN: 'ADM',
                UserRole.GESTOR: 'GST',
                UserRole.REGISTRADO: 'USR',
            }
            prefix = prefix_map.get(self.role, 'USR')
            total_users_same_role = User.objects.filter(role=self.role).count() + 1
            self.custom_id = f"{prefix}-2026-{total_users_same_role:05d}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.custom_id} - {self.email}"


class GuestSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session_key = models.CharField(max_length=40, unique=True, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Invitado {self.session_key[:8]}"


class UserUsageQuota(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='usage_quotas')
    guest_session = models.ForeignKey(GuestSession, on_delete=models.CASCADE, null=True, blank=True, related_name='usage_quotas')
    date = models.DateField(db_index=True)
    messages_sent = models.IntegerField(default=0)
    max_limit = models.IntegerField(default=50)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'date'], name='unique_user_daily_quota'),
            models.UniqueConstraint(fields=['guest_session', 'date'], name='unique_guest_daily_quota'),
        ]

    def __str__(self):
        entity = self.user.email if self.user else str(self.guest_session)
        return f"{entity} [{self.date}]: {self.messages_sent}/{self.max_limit}"


# ==========================================
# 2. MÓDULO DE LEYES Y VECTORES (RAG)
# ==========================================

class LawStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pendiente'
    EXTRACTING = 'EXTRACTING', 'Extrayendo Texto'
    INDEXED = 'INDEXED', 'Indexado / Vectorizado'
    FAILED = 'FAILED', 'Error en Procesamiento'


class FederalLaw(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    official_title = models.CharField('Título Oficial de la Ley', max_length=500, db_index=True)
    short_title = models.CharField('Siglas / Nombre Corto', max_length=100, null=True, blank=True)
    dof_publication_date = models.DateField('Fecha Publicación DOF', null=True, blank=True)
    dof_last_reform_date = models.DateField('Última Reforma DOF', null=True, blank=True)
    pdf_file = models.FileField('Archivo PDF', upload_to='laws_pdf/')
    
    # Nivel 1 Anti-Duplicidad: Hash SHA-256 del archivo
    file_hash = models.CharField('Hash SHA-256 PDF', max_length=64, unique=True, db_index=True)
    
    status = models.CharField('Estado', max_length=20, choices=LawStatus.choices, default=LawStatus.PENDING)
    is_active = models.BooleanField('Vigente en RAG', default=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='uploaded_laws'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        estado = "Vigente" if self.is_active else "Derogada/Histórica"
        return f"{self.official_title} ({estado})"


class SectionType(models.TextChoices):
    TITULO = 'TITULO', 'Título'
    CAPITULO = 'CAPITULO', 'Capítulo'
    ARTICULO = 'ARTICULO', 'Artículo'
    TRANSITORIO = 'TRANSITORIO', 'Transitorio'


class LawSection(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    law = models.ForeignKey(FederalLaw, on_delete=models.CASCADE, related_name='sections')
    section_type = models.CharField('Tipo', max_length=20, choices=SectionType.choices)
    article_number = models.CharField('Número de Artículo', max_length=50, null=True, blank=True, db_index=True)
    title = models.CharField('Título de la Sección', max_length=255)
    raw_content = models.TextField('Texto Íntegro')
    order = models.IntegerField('Orden Cronológico', db_index=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.law.short_title or self.law.official_title[:20]} - {self.title}"


class LawChunk(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    law = models.ForeignKey(FederalLaw, on_delete=models.CASCADE, related_name='chunks')
    section = models.ForeignKey(LawSection, on_delete=models.CASCADE, related_name='chunks')
    article_reference = models.CharField('Referencia para Prompt', max_length=150)
    content = models.TextField('Texto del Fragmento')
    
    # Nivel 2 Anti-Duplicidad: Hash del texto del fragmento
    chunk_hash = models.CharField('Hash SHA-256 Fragmento', max_length=64, unique=True, db_index=True)
    
    # Vector de 1024 dimensiones (para modelos como BAAI/bge-m3)
    embedding = VectorField(dimensions=1024)
    metadata = models.JSONField('Metadatos Adicionales', default=dict)

    def __str__(self):
        return f"Chunk {self.article_reference} [{str(self.id)[:8]}]"


# ==========================================
# 3. MÓDULO DE ASISTENTE CONVERSACIONAL Y CITAS
# ==========================================

class ChatRole(models.TextChoices):
    USER = 'USER', 'Usuario'
    ASSISTANT = 'ASSISTANT', 'Asistente IA'
    SYSTEM = 'SYSTEM', 'Sistema'


class ChatSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='chat_sessions'
    )
    guest_session = models.ForeignKey(
        GuestSession,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='chat_sessions'
    )
    title = models.CharField('Título de la Conversación', max_length=255, default='Nueva Consulta Legal')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Chat: {self.title} ({self.created_at.strftime('%Y-%m-%d')})"


class ChatMessage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField('Emisor', max_length=10, choices=ChatRole.choices)
    content = models.TextField('Mensaje')
    
    # Guardrail: Bloqueo de consultas fuera del marco legal mexicano
    is_out_of_scope = models.BooleanField('Fuera de Ámbito (Guardrail)', default=False)
    
    llm_provider = models.CharField('Proveedor LLM', max_length=20, null=True, blank=True)
    llm_model = models.CharField('Modelo LLM', max_length=50, null=True, blank=True)
    tokens_used = models.IntegerField('Tokens Consumidos', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"[{self.role}] {self.content[:30]}..."


class MessageCitation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    message = models.ForeignKey(ChatMessage, on_delete=models.CASCADE, related_name='citations')
    chunk = models.ForeignKey(LawChunk, on_delete=models.PROTECT, related_name='citations')
    law_title = models.CharField('Título de Ley Citada', max_length=500)
    article_reference = models.CharField('Artículo Citado', max_length=150)
    relevance_score = models.FloatField('Similitud Semántica')

    def __str__(self):
        return f"Cita {self.article_reference} -> Msg {str(self.message.id)[:8]}"