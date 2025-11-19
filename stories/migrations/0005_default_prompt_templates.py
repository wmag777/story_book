# Data migration to create default prompt templates

from django.db import migrations


def create_default_templates(apps, schema_editor):
    PromptTemplate = apps.get_model('stories', 'PromptTemplate')

    default_templates = [
        {
            'name': 'Story Scene Extraction',
            'template_type': 'scene_extraction',
            'template_text': """Extract the main scenes of the [STORY] focusing on what could be turned into an image for the book. [STORY]: {story}""",
            'description': 'Extracts visual scenes from a story that can be illustrated',
            'variables': ['story'],
            'is_active': True
        },
        {
            'name': 'Character Description Extraction',
            'template_type': 'character_extraction',
            'template_text': """Extract a list of the MAIN characters of the [STORY] and for each character generate description that can identify him if want to draw in a max of 15 words.
Example:
character name: Ali
character description: a 10-year-old boy, with brown hair, wearing a red t-shirt and blue jeans.
[STORY]: {story}""",
            'description': 'Extracts characters with visual descriptions from a story',
            'variables': ['story'],
            'is_active': True
        },
        {
            'name': 'Image Style Suffix',
            'template_type': 'image_style_suffix',
            'template_text': ' Draw in {style} with {color_scheme} colors.',
            'description': 'Added to image prompts to specify artistic style and color scheme',
            'variables': ['style', 'color_scheme'],
            'is_active': True
        },
        {
            'name': 'Stability AI Negative Prompt',
            'template_type': 'stability_negative',
            'template_text': 'blurry, bad quality, distorted',
            'description': 'Negative prompt for Stability AI to avoid unwanted image characteristics',
            'variables': [],
            'is_active': True
        }
    ]

    for template_data in default_templates:
        PromptTemplate.objects.get_or_create(
            template_type=template_data['template_type'],
            defaults=template_data
        )


def reverse_templates(apps, schema_editor):
    PromptTemplate = apps.get_model('stories', 'PromptTemplate')
    PromptTemplate.objects.filter(
        template_type__in=[
            'scene_extraction',
            'character_extraction',
            'image_style_suffix',
            'stability_negative'
        ]
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('stories', '0004_prompttemplate'),
    ]

    operations = [
        migrations.RunPython(create_default_templates, reverse_templates),
    ]