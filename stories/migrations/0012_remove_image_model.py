# Generated migration to remove image_model field from Project

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('stories', '0011_remove_edit_mode'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='project',
            name='image_model',
        ),
    ]