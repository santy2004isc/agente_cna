from django.db import migrations
from pgvector.django import VectorExtension

class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        # Activa la extensión pgvector en PostgreSQL
        VectorExtension(),
    ]