# Generated manually for adding image_model field to Project

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('stories', '0002_project_color_scheme'),
    ]

    operations = [
        migrations.AddField(
            model_name='project',
            name='image_model',
            field=models.CharField(
                choices=[
                    ('google_nano_banana', 'Google Nano Banana'),
                    ('stability_ai', 'Stability AI'),
                    ('seedance', 'Seedance (Coming Soon)')
                ],
                default='google_nano_banana',
                help_text='AI model to use for image generation',
                max_length=50
            ),
        ),
    ]