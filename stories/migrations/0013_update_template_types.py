# Migration to update template types: remove stability_negative, add reference_image_instruction

from django.db import migrations, models


def update_templates(apps, schema_editor):
    PromptTemplate = apps.get_model('stories', 'PromptTemplate')

    # Delete the stability_negative template if it exists
    PromptTemplate.objects.filter(template_type='stability_negative').delete()

    # Create the new reference_image_instruction template
    PromptTemplate.objects.get_or_create(
        template_type='reference_image_instruction',
        defaults={
            'name': 'Reference Image Instruction',
            'template_text': ' Use the exact appearance of {character_names} from the provided reference image{plural}.',
            'description': 'Instruction for using character reference images in generation. Use {character_names} for the names and {plural} for "s" when multiple.',
            'variables': ['character_names', 'plural'],
            'is_active': True
        }
    )


def reverse_update(apps, schema_editor):
    PromptTemplate = apps.get_model('stories', 'PromptTemplate')

    # Delete the reference_image_instruction template
    PromptTemplate.objects.filter(template_type='reference_image_instruction').delete()

    # Recreate the stability_negative template
    PromptTemplate.objects.get_or_create(
        template_type='stability_negative',
        defaults={
            'name': 'Stability AI Negative Prompt',
            'template_text': 'blurry, bad quality, distorted',
            'description': 'Negative prompt for Stability AI to avoid unwanted image characteristics',
            'variables': [],
            'is_active': True
        }
    )


class Migration(migrations.Migration):

    dependencies = [
        ('stories', '0012_remove_image_model'),
    ]

    operations = [
        # First update the model field to include new choice and keep old for data migration
        migrations.AlterField(
            model_name='prompttemplate',
            name='template_type',
            field=models.CharField(
                choices=[
                    ('scene_extraction', 'Scene Extraction'),
                    ('character_extraction', 'Character Extraction'),
                    ('image_style_suffix', 'Image Style Suffix'),
                    ('reference_image_instruction', 'Reference Image Instruction'),
                    ('stability_negative', 'Stability Negative Prompt')  # Keep temporarily for migration
                ],
                help_text='Type of prompt template',
                max_length=50,
                unique=True
            ),
        ),
        # Run the data migration
        migrations.RunPython(update_templates, reverse_update),
        # Finally update to remove the old choice
        migrations.AlterField(
            model_name='prompttemplate',
            name='template_type',
            field=models.CharField(
                choices=[
                    ('scene_extraction', 'Scene Extraction'),
                    ('character_extraction', 'Character Extraction'),
                    ('image_style_suffix', 'Image Style Suffix'),
                    ('reference_image_instruction', 'Reference Image Instruction'),
                ],
                help_text='Type of prompt template',
                max_length=50,
                unique=True
            ),
        ),
    ]