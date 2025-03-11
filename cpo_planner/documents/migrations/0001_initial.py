# Generated manually (normally by 'python manage.py makemigrations')

from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings

class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('cpo_core', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProjectDocument',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=255, verbose_name='Titolo')),
                ('file', models.FileField(upload_to='project_documents/', verbose_name='File')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Data Creazione')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Ultimo Aggiornamento')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='created_project_documents', to=settings.AUTH_USER_MODEL, verbose_name='Creato da')),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='documents', to='cpo_core.project')),
            ],
            options={
                'verbose_name': 'Documento Progetto',
                'verbose_name_plural': 'Documenti Progetto',
            },
        ),
    ]