from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('stories', '0015_generationsettings_google_api_key_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='generationsettings',
            name='artemox_api_key',
            field=models.CharField(
                max_length=255,
                blank=True,
                default='',
                help_text='Artemox API key (overrides environment variable if set)',
            ),
        ),
        migrations.AddField(
            model_name='generationsettings',
            name='artemox_base_url',
            field=models.CharField(
                max_length=255,
                blank=True,
                default='',
                help_text='Artemox Base URL (overrides environment variable if set)',
            ),
        ),
        migrations.AddField(
            model_name='generationsettings',
            name='ai_provider',
            field=models.CharField(
                max_length=20,
                choices=[
                    ('openai', 'OpenAI'),
                    ('artemox', 'Artemox'),
                ],
                default='openai',
                help_text='Select which AI provider to use for text generation',
            ),
        ),
    ]

