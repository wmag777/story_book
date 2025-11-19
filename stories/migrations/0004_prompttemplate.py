# Generated manually for PromptTemplate model

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('stories', '0003_project_image_model'),
    ]

    operations = [
        migrations.CreateModel(
            name='PromptTemplate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='Descriptive name for this template', max_length=200)),
                ('template_type', models.CharField(
                    choices=[
                        ('scene_extraction', 'Scene Extraction'),
                        ('character_extraction', 'Character Extraction'),
                        ('image_style_suffix', 'Image Style Suffix'),
                        ('stability_negative', 'Stability Negative Prompt')
                    ],
                    help_text='Type of prompt template',
                    max_length=50,
                    unique=True
                )),
                ('template_text', models.TextField(help_text='The prompt template text. Use {variable} for placeholders.')),
                ('description', models.TextField(help_text='Explain what this prompt does and how to use it')),
                ('variables', models.JSONField(blank=True, default=list, help_text="List of variables used in this template (e.g., ['story', 'style'])")),
                ('is_active', models.BooleanField(default=True, help_text='Whether this template is currently active')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Prompt Template',
                'verbose_name_plural': 'Prompt Templates',
                'ordering': ['template_type', 'name'],
            },
        ),
    ]