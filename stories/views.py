from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, CreateView, DetailView
from django.urls import reverse_lazy
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.core.cache import cache
import re
import json
import time

from .models import Project, Character, Scene, PromptTemplate, GenerationSettings, GenerationCost
from .services.story_processing import StoryProcessor
from .services.image_generation import ImageGenerator
from .services.character_generation import CharacterGenerator
from .forms import PromptTemplateForm, PromptTestForm, GenerationSettingsForm
from decimal import Decimal
from django.db.models import Sum, Count, Q


class ProjectListView(ListView):
    model = Project
    template_name = 'stories/project_list.html'
    context_object_name = 'projects'


class ProjectCreateView(CreateView):
    model = Project
    template_name = 'stories/project_form.html'
    fields = ['name', 'style', 'color_scheme']
    success_url = reverse_lazy('project_list')


def project_detail(request, pk):
    project = get_object_or_404(Project, pk=pk)
    characters = project.characters.all()
    scenes = project.scenes.all()

    context = {
        'project': project,
        'characters': characters,
        'scenes': scenes,
        'styles': [
            "Ghibli-style", "line-art-style", "pixel-art-style",
            "water-color-style", "Fairy-Tale-style", "Game-RPG-Style",
            "Game-Zelda-Style", "Manga-style", "Pixar-3d-style",
            "Anime-style", "Watercolor-style", "Cinematic-style",
            "wimpy-kid-style"
        ],
        'color_schemes': [
            "colored", "black-and-white", "grayscale",
            "sepia", "monochrome", "vibrant", "pastel"
        ]
    }
    return render(request, 'stories/project_detail.html', context)


def story_input(request, pk):
    project = get_object_or_404(Project, pk=pk)

    if request.method == 'POST':
        story_text = request.POST.get('story_text', '')

        if story_text:
            try:
                processor = StoryProcessor()

                # Extract characters
                extracted_characters = processor.extract_characters(story_text)

                # Save characters to database
                for char in extracted_characters:
                    Character.objects.create(
                        project=project,
                        name=char.name,
                        description=char.description
                    )

                # Extract scenes
                extracted_scenes = processor.extract_scenes(story_text)

                # Process scenes with character placeholders
                for i, scene_text in enumerate(extracted_scenes):
                    processed_scene = scene_text

                    # Replace character names with placeholders
                    for char in extracted_characters:
                        processed_scene = re.sub(
                            r'\b' + re.escape(char.name) + r'\b',
                            f"{{{char.name}}}",
                            processed_scene,
                            flags=re.IGNORECASE
                        )

                    # Create scene in database
                    scene = Scene.objects.create(
                        project=project,
                        name=f"Scene {i+1}",
                        prompt=processed_scene,
                        order=i+1
                    )

                    # Auto-detect and link characters mentioned in the scene
                    for char in extracted_characters:
                        if f"{{{char.name}}}" in processed_scene:
                            # Get the Character object from database
                            db_char = Character.objects.filter(project=project, name=char.name).first()
                            if db_char:
                                scene.characters.add(db_char)

                messages.success(request, f"Extracted {len(extracted_characters)} characters and {len(extracted_scenes)} scenes!")
                return redirect('project_detail', pk=project.pk)

            except Exception as e:
                messages.error(request, f"Error processing story: {str(e)}")

    return render(request, 'stories/story_input.html', {'project': project})


def scene_manager(request, project_pk, scene_pk):
    project = get_object_or_404(Project, pk=project_pk)
    scene = get_object_or_404(Scene, pk=scene_pk, project=project)

    if request.method == 'POST':
        # Update scene prompt
        new_prompt = request.POST.get('prompt', '')
        if new_prompt:
            scene.prompt = new_prompt

        # Update custom final prompt if provided
        final_prompt = request.POST.get('final_prompt', '')
        use_custom = request.POST.get('use_custom_prompt') == 'on'

        scene.final_prompt = final_prompt
        scene.use_custom_prompt = use_custom

        # Update selected characters
        selected_character_ids = request.POST.getlist('characters')
        scene.characters.set(selected_character_ids)

        scene.save()
        messages.success(request, "Scene updated successfully!")

    # Generate the final prompt preview - EXACTLY as it will be sent to the API
    from .services.image_generation import ImageGenerator
    from .models import PromptTemplate

    generator = ImageGenerator()
    characters = project.characters.all()
    selected_chars = scene.characters.all()

    # Check which characters have images for smarter replacement
    characters_with_images = set()
    for char in selected_chars:
        if char.generated_image:
            characters_with_images.add(char.name)

    # Replace character placeholders - use minimal replacement if images available
    use_references = bool(characters_with_images)
    preview_prompt = generator.replace_character_placeholders(
        scene.prompt,
        characters,
        use_references=use_references,
        characters_with_images=characters_with_images
    )

    # Add style suffix from template
    style_suffix = ""
    style_template_status = ""
    try:
        style_template = PromptTemplate.objects.get(
            template_type='image_style_suffix',
            is_active=True
        )
        style_suffix = style_template.render(
            style=project.style,
            color_scheme=project.color_scheme
        )
        style_template_status = f"Using template: '{style_template.name}'"
        print(f"Using style template: {style_suffix}")
    except PromptTemplate.DoesNotExist:
        style_template_status = "WARNING: Style template not found in database"
        print("WARNING: image_style_suffix template not found in database")
    except ValueError as e:
        style_template_status = f"ERROR: Template rendering failed: {e}"
        print(f"ERROR rendering style template: {e}")

    preview_prompt += style_suffix

    # Add reference image instructions
    reference_notes = []
    if characters_with_images:
        # Add a single, clear instruction for all characters with images
        char_names = [char.name for char in selected_chars if char.reference_image or char.generated_image]
        if char_names:
            # Use template for reference image instruction
            try:
                ref_template = PromptTemplate.objects.get(
                    template_type='reference_image_instruction',
                    is_active=True
                )
                if len(char_names) == 1:
                    ref_instruction = ref_template.render(
                        character_names=char_names[0],
                        plural=''
                    )
                else:
                    names_str = ', '.join(char_names[:-1]) + f' and {char_names[-1]}'
                    ref_instruction = ref_template.render(
                        character_names=names_str,
                        plural='s'
                    )
                preview_prompt += ref_instruction
            except PromptTemplate.DoesNotExist:
                # Fallback if template not found
                if len(char_names) == 1:
                    preview_prompt += f" Use the exact appearance of {char_names[0]} from the provided reference image."
                else:
                    names_str = ', '.join(char_names[:-1]) + f' and {char_names[-1]}'
                    preview_prompt += f" Use the exact appearance of {names_str} from the provided reference images."

            for name in char_names:
                reference_notes.append(f"{name} (image will be passed)")

    # Use custom prompt if available and enabled
    if scene.use_custom_prompt and scene.final_prompt:
        preview_prompt = scene.final_prompt
        reference_notes = ["Custom prompt mode - reference images may still be passed"]

    context = {
        'project': project,
        'scene': scene,
        'characters': project.characters.all(),
        'selected_characters': scene.characters.all(),
        'final_prompt_preview': preview_prompt,
        'reference_notes': reference_notes,
        'style_template_status': style_template_status
    }
    return render(request, 'stories/scene_manager.html', context)


@require_POST
def generate_image(request, project_pk, scene_pk):
    project = get_object_or_404(Project, pk=project_pk)
    scene = get_object_or_404(Scene, pk=scene_pk, project=project)

    try:
        generator = ImageGenerator()

        # GENERATION MODE: Generate new image
        if scene.use_custom_prompt and scene.final_prompt:
            final_prompt = scene.final_prompt

            # Gather reference images for selected characters
            reference_images = []
            char_names_with_images = []
            for character in scene.characters.all():
                # Check for reference_image first (manually uploaded), then generated_image
                if character.reference_image:
                    # Get the full path to the manually uploaded image
                    image_path = character.reference_image.path
                    reference_images.append(image_path)
                    char_names_with_images.append(character.name)
                elif character.generated_image:
                    # Get the full path to the AI-generated image
                    image_path = character.generated_image.path
                    reference_images.append(image_path)
                    char_names_with_images.append(character.name)

            # Add a single, clear instruction for all characters with images
            if char_names_with_images:
                # Use template for reference image instruction
                try:
                    ref_template = PromptTemplate.objects.get(
                        template_type='reference_image_instruction',
                        is_active=True
                    )
                    if len(char_names_with_images) == 1:
                        ref_instruction = ref_template.render(
                            character_names=char_names_with_images[0],
                            plural=''
                        )
                    else:
                        names_str = ', '.join(char_names_with_images[:-1]) + f' and {char_names_with_images[-1]}'
                        ref_instruction = ref_template.render(
                            character_names=names_str,
                            plural='s'
                        )
                    final_prompt += ref_instruction
                except PromptTemplate.DoesNotExist:
                    # Fallback if template not found
                    if len(char_names_with_images) == 1:
                        final_prompt += f" Use the exact appearance of {char_names_with_images[0]} from the provided reference image."
                    else:
                        names_str = ', '.join(char_names_with_images[:-1]) + f' and {char_names_with_images[-1]}'
                        final_prompt += f" Use the exact appearance of {names_str} from the provided reference images."

            # Generate image using Nano Banana
            filename_base = f"project_{project.pk}_scene_{scene.pk}"
            image_file = generator.generate(final_prompt, filename_base, reference_images=reference_images, project=project, scene=scene)

            # Save image to scene
            scene.approved_image = image_file
            scene.save()

            messages.success(request, "Image generated successfully!")

        else:
            # Get the prompt and replace character placeholders
            prompt = scene.prompt
            characters = project.characters.all()

            # Check which selected characters have images
            characters_with_images = set()
            for char in scene.characters.all():
                # Check for reference_image first, then generated_image
                if char.reference_image or char.generated_image:
                    characters_with_images.add(char.name)

            # Use minimal replacement when reference images are available
            use_references = bool(characters_with_images)
            final_prompt = generator.replace_character_placeholders(
                prompt,
                characters,
                use_references=use_references,
                characters_with_images=characters_with_images
            )

            # Add style and color scheme to prompt using template
            from .models import PromptTemplate
            style_suffix = ""
            try:
                style_template = PromptTemplate.objects.get(
                    template_type='image_style_suffix',
                    is_active=True
                )
                style_suffix = style_template.render(
                    style=project.style,
                    color_scheme=project.color_scheme
                )
                print(f"Using style template: {style_suffix}")
            except PromptTemplate.DoesNotExist:
                print("WARNING: image_style_suffix template not found for generation")
            except ValueError as e:
                print(f"ERROR rendering style template: {e}")
            final_prompt += style_suffix

            # Gather reference images for selected characters
            reference_images = []
            char_names_with_images = []
            for character in scene.characters.all():
                # Check for reference_image first (manually uploaded), then generated_image
                if character.reference_image:
                    # Get the full path to the manually uploaded image
                    image_path = character.reference_image.path
                    reference_images.append(image_path)
                    char_names_with_images.append(character.name)
                elif character.generated_image:
                    # Get the full path to the AI-generated image
                    image_path = character.generated_image.path
                    reference_images.append(image_path)
                    char_names_with_images.append(character.name)

            # Add a single, clear instruction for all characters with images
            if char_names_with_images:
                # Use template for reference image instruction
                try:
                    ref_template = PromptTemplate.objects.get(
                        template_type='reference_image_instruction',
                        is_active=True
                    )
                    if len(char_names_with_images) == 1:
                        ref_instruction = ref_template.render(
                            character_names=char_names_with_images[0],
                            plural=''
                        )
                    else:
                        names_str = ', '.join(char_names_with_images[:-1]) + f' and {char_names_with_images[-1]}'
                        ref_instruction = ref_template.render(
                            character_names=names_str,
                            plural='s'
                        )
                    final_prompt += ref_instruction
                except PromptTemplate.DoesNotExist:
                    # Fallback if template not found
                    if len(char_names_with_images) == 1:
                        final_prompt += f" Use the exact appearance of {char_names_with_images[0]} from the provided reference image."
                    else:
                        names_str = ', '.join(char_names_with_images[:-1]) + f' and {char_names_with_images[-1]}'
                        final_prompt += f" Use the exact appearance of {names_str} from the provided reference images."

            # Generate image using Nano Banana
            filename_base = f"project_{project.pk}_scene_{scene.pk}"
            image_file = generator.generate(final_prompt, filename_base, reference_images=reference_images, project=project, scene=scene)

            # Save image to scene
            scene.approved_image = image_file
            scene.save()

            messages.success(request, "Image generated successfully!")

    except Exception as e:
        messages.error(request, f"Error generating image: {str(e)}")

    return redirect('scene_manager', project_pk=project.pk, scene_pk=scene.pk)


@require_POST
def generate_image_ajax(request, project_pk, scene_pk):
    """AJAX endpoint for async image generation with progress updates"""
    project = get_object_or_404(Project, pk=project_pk)
    scene = get_object_or_404(Scene, pk=scene_pk, project=project)

    try:
        # Send initial status
        response_data = {
            'status': 'processing',
            'message': 'Initializing image generation...'
        }

        generator = ImageGenerator()

        # Check if we should use custom prompt
        if scene.use_custom_prompt and scene.final_prompt:
            final_prompt = scene.final_prompt
        else:
            # Get the prompt and replace character placeholders
            prompt = scene.prompt
            characters = project.characters.all()

            # Check which selected characters have images
            characters_with_images = set()
            for char in scene.characters.all():
                # Check for reference_image first, then generated_image
                if char.reference_image or char.generated_image:
                    characters_with_images.add(char.name)

            # Use minimal replacement when reference images are available
            use_references = bool(characters_with_images)
            final_prompt = generator.replace_character_placeholders(
                prompt,
                characters,
                use_references=use_references,
                characters_with_images=characters_with_images
            )

            # Add style and color scheme to prompt using template
            from .models import PromptTemplate
            style_suffix = ""
            try:
                style_template = PromptTemplate.objects.get(
                    template_type='image_style_suffix',
                    is_active=True
                )
                style_suffix = style_template.render(
                    style=project.style,
                    color_scheme=project.color_scheme
                )
                print(f"Using style template: {style_suffix}")
            except PromptTemplate.DoesNotExist:
                print("WARNING: image_style_suffix template not found for generation")
            except ValueError as e:
                print(f"ERROR rendering style template: {e}")
            final_prompt += style_suffix

        # Gather reference images for selected characters
        reference_images = []
        char_names_with_images = []
        for character in scene.characters.all():
            # Check for reference_image first (manually uploaded), then generated_image
            if character.reference_image:
                # Get the full path to the manually uploaded image
                image_path = character.reference_image.path
                reference_images.append(image_path)
                char_names_with_images.append(character.name)
            elif character.generated_image:
                # Get the full path to the AI-generated image
                image_path = character.generated_image.path
                reference_images.append(image_path)
                char_names_with_images.append(character.name)

        # Add a single, clear instruction for all characters with images
        if char_names_with_images:
            # Use template for reference image instruction
            try:
                ref_template = PromptTemplate.objects.get(
                    template_type='reference_image_instruction',
                    is_active=True
                )
                if len(char_names_with_images) == 1:
                    ref_instruction = ref_template.render(
                        character_names=char_names_with_images[0],
                        plural=''
                    )
                else:
                    names_str = ', '.join(char_names_with_images[:-1]) + f' and {char_names_with_images[-1]}'
                    ref_instruction = ref_template.render(
                        character_names=names_str,
                        plural='s'
                    )
                final_prompt += ref_instruction
            except PromptTemplate.DoesNotExist:
                # Fallback if template not found
                if len(char_names_with_images) == 1:
                    final_prompt += f" Use the exact appearance of {char_names_with_images[0]} from the provided reference image."
                else:
                    names_str = ', '.join(char_names_with_images[:-1]) + f' and {char_names_with_images[-1]}'
                    final_prompt += f" Use the exact appearance of {names_str} from the provided reference images."

        # Generate image
        filename_base = f"project_{project.pk}_scene_{scene.pk}"

        # In a real implementation, you might want to use Celery for true async
        # For now, we'll generate synchronously but return progress updates
        response_data['message'] = 'Generating image with Google Nano Banana...'

        image_file = generator.generate(final_prompt, filename_base, reference_images=reference_images, project=project, scene=scene)

        # Save image to scene
        scene.approved_image = image_file
        scene.save()

        # Return success with image URL
        response_data = {
            'status': 'success',
            'message': 'Image generated successfully!',
            'image_url': scene.approved_image.url if scene.approved_image else None
        }

    except Exception as e:
        response_data = {
            'status': 'error',
            'message': f'Error generating image: {str(e)}'
        }

    return JsonResponse(response_data)


def story_viewer(request, pk):
    project = get_object_or_404(Project, pk=pk)
    scenes = project.scenes.all()

    context = {
        'project': project,
        'scenes': scenes
    }
    return render(request, 'stories/story_viewer.html', context)


def delete_project(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if request.method == 'POST':
        project.delete()
        messages.success(request, "Project deleted successfully!")
        return redirect('project_list')
    return redirect('project_detail', pk=pk)


def update_style(request, pk):
    if request.method == 'POST':
        project = get_object_or_404(Project, pk=pk)
        new_style = request.POST.get('style')
        if new_style:
            project.style = new_style
            project.save()
            messages.success(request, f"Style updated to {new_style}")
    return redirect('project_detail', pk=pk)


def character_add(request, project_pk):
    project = get_object_or_404(Project, pk=project_pk)

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()

        if name and description:
            Character.objects.create(
                project=project,
                name=name,
                description=description
            )
            messages.success(request, f"Character '{name}' added successfully!")
            return redirect('project_detail', pk=project.pk)
        else:
            messages.error(request, "Please provide both name and description.")

    context = {
        'project': project
    }
    return render(request, 'stories/character_add.html', context)


def character_edit(request, project_pk, character_pk):
    from .forms import CharacterEditForm

    project = get_object_or_404(Project, pk=project_pk)
    character = get_object_or_404(Character, pk=character_pk, project=project)

    if request.method == 'POST':
        old_name = character.name
        form = CharacterEditForm(request.POST, request.FILES, instance=character)
        update_placeholders = request.POST.get('update_placeholders') == 'on'
        remove_image = request.POST.get('remove_image') == 'on'

        if form.is_valid():
            new_name = form.cleaned_data['name']

            # Update placeholders in scenes if name changed and user requested it
            if old_name != new_name and update_placeholders:
                scenes = project.scenes.all()
                for scene in scenes:
                    # Replace old placeholder with new placeholder
                    scene.prompt = scene.prompt.replace(f"{{{old_name}}}", f"{{{new_name}}}")
                    scene.save()
                messages.info(request, f"Updated character placeholders in {scenes.count()} scenes.")

            # Handle manual image upload
            if form.cleaned_data.get('manual_image'):
                # Delete old reference image if it exists
                if character.reference_image:
                    character.reference_image.delete(save=False)
                # Save new reference image
                character.reference_image = form.cleaned_data['manual_image']
                messages.success(request, "Character image uploaded successfully!")

            # Handle image removal
            if remove_image:
                if character.reference_image:
                    character.reference_image.delete(save=False)
                    character.reference_image = None
                if character.generated_image:
                    character.generated_image.delete(save=False)
                    character.generated_image = None
                messages.info(request, "Character image removed.")

            # Save character
            form.save()
            messages.success(request, f"Character '{new_name}' updated successfully!")
            return redirect('project_detail', pk=project.pk)
        else:
            # Show form errors
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = CharacterEditForm(instance=character)

    context = {
        'project': project,
        'character': character,
        'form': form
    }
    return render(request, 'stories/character_edit.html', context)


def character_delete(request, project_pk, character_pk):
    project = get_object_or_404(Project, pk=project_pk)
    character = get_object_or_404(Character, pk=character_pk, project=project)

    if request.method == 'POST':
        character_name = character.name
        character.delete()
        messages.success(request, f"Character '{character_name}' deleted successfully!")
        return redirect('project_detail', pk=project.pk)

    return redirect('character_edit', project_pk=project.pk, character_pk=character.pk)


def update_color_scheme(request, pk):
    if request.method == 'POST':
        project = get_object_or_404(Project, pk=pk)
        new_color_scheme = request.POST.get('color_scheme')
        if new_color_scheme:
            project.color_scheme = new_color_scheme
            project.save()
            messages.success(request, f"Color scheme updated to {new_color_scheme}")
    return redirect('project_detail', pk=pk)




# Prompt Template Management Views
def prompt_template_list(request):
    """List all prompt templates."""
    templates = PromptTemplate.objects.all()
    return render(request, 'stories/prompt_template_list.html', {
        'templates': templates
    })


def prompt_template_edit(request, pk):
    """Edit a prompt template."""
    template = get_object_or_404(PromptTemplate, pk=pk)

    if request.method == 'POST':
        form = PromptTemplateForm(request.POST, instance=template)
        if form.is_valid():
            form.save()
            messages.success(request, f"Prompt template '{template.name}' updated successfully!")
            return redirect('prompt_template_list')
    else:
        form = PromptTemplateForm(instance=template)

    # Test form for preview
    test_form = PromptTestForm()

    return render(request, 'stories/prompt_template_edit.html', {
        'form': form,
        'test_form': test_form,
        'template': template
    })


@require_POST
def prompt_template_test(request, pk):
    """Test a prompt template with sample data."""
    template = get_object_or_404(PromptTemplate, pk=pk)

    # Get template text from form or use existing
    template_text = request.POST.get('template_text', template.template_text)

    test_form = PromptTestForm(request.POST)
    if test_form.is_valid():
        test_data = test_form.cleaned_data['test_data']

        try:
            # Create temporary template for testing
            temp_template = PromptTemplate(template_text=template_text)
            rendered = temp_template.render(**test_data)

            return JsonResponse({
                'status': 'success',
                'rendered': rendered,
                'variables': temp_template.get_variables_from_template()
            })
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=400)
    else:
        return JsonResponse({
            'status': 'error',
            'message': 'Invalid test data',
            'errors': test_form.errors
        }, status=400)


@require_POST
def prompt_template_reset(request, pk):
    """Reset a prompt template to its default value."""
    template = get_object_or_404(PromptTemplate, pk=pk)

    # Get default templates
    defaults = PromptTemplate.get_default_templates()

    # Find matching default by template type
    default_template = next(
        (t for t in defaults if t['template_type'] == template.template_type),
        None
    )

    if default_template:
        template.name = default_template['name']
        template.template_text = default_template['template_text']
        template.description = default_template['description']
        template.variables = default_template['variables']
        template.save()

        # Clear cache
        cache_key = f'prompt_template_{template.template_type}'
        cache.delete(cache_key)

        messages.success(request, f"Prompt template '{template.name}' reset to default!")
    else:
        messages.error(request, "No default template found for this type.")

    return redirect('prompt_template_edit', pk=pk)


def clear_prompt_cache(request):
    """Clear all cached prompt templates."""
    # Clear specific cache keys
    template_types = ['scene_extraction', 'character_extraction', 'image_style_suffix']
    for template_type in template_types:
        cache_key = f'prompt_template_{template_type}'
        cache.delete(cache_key)

    messages.success(request, "Prompt template cache cleared successfully!")
    return redirect('prompt_template_list')


def character_generate(request, project_pk):
    """Generate a new character with AI-generated image."""
    project = get_object_or_404(Project, pk=project_pk)

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        generation_prompt = request.POST.get('generation_prompt', '').strip()
        generate_image = request.POST.get('generate_image') == 'on'

        if name and description:
            # Create the character
            character = Character.objects.create(
                project=project,
                name=name,
                description=description,
                generation_prompt=generation_prompt or description
            )

            # Generate image if requested
            if generate_image and generation_prompt:
                try:
                    generator = CharacterGenerator()
                    image_file = generator.generate_character(
                        generation_prompt or description,
                        name,
                        project_style=project.style,
                        project_color_scheme=project.color_scheme,
                        project=project,
                        character=character
                    )
                    character.generated_image = image_file
                    character.save()
                    messages.success(request, f"Character '{name}' created with generated image!")
                except Exception as e:
                    messages.warning(request, f"Character created but image generation failed: {str(e)}")
            else:
                messages.success(request, f"Character '{name}' created successfully!")

            return redirect('project_detail', pk=project.pk)
        else:
            messages.error(request, "Please provide both name and description.")

    context = {
        'project': project,
        'styles': [
            "Ghibli-style", "line-art-style", "pixel-art-style",
            "water-color-style", "Fairy-Tale-style", "Game-RPG-Style",
            "Game-Zelda-Style", "Manga-style", "Pixar-3d-style",
            "Anime-style", "Watercolor-style", "Cinematic-style",
            "wimpy-kid-style"
        ]
    }
    return render(request, 'stories/character_generate.html', context)


@require_POST
def edit_scene_image(request, project_pk, scene_pk):
    """Dedicated endpoint for editing scene images - completely separate from generation."""
    project = get_object_or_404(Project, pk=project_pk)
    scene = get_object_or_404(Scene, pk=scene_pk, project=project)

    # Only allow editing if image exists
    if not scene.approved_image:
        messages.error(request, "No image to edit. Please generate an image first.")
        return redirect('scene_manager', project_pk=project.pk, scene_pk=scene.pk)


    # Get edit prompt from form
    edit_prompt = request.POST.get('edit_prompt', '').strip()
    if not edit_prompt:
        messages.error(request, "Please provide edit instructions")
        return redirect('scene_manager', project_pk=project.pk, scene_pk=scene.pk)

    try:
        generator = ImageGenerator()

        # Edit the image - ONLY pass the current image and edit prompt
        filename_base = f"project_{project.pk}_scene_{scene.pk}_edited"
        image_file = generator.edit_image(
            scene.approved_image.path,
            edit_prompt,
            filename_base,
            project=project,
            scene=scene
        )

        # Save the edited image and the edit prompt
        scene.approved_image = image_file
        scene.edit_prompt = edit_prompt
        scene.save()

        messages.success(request, "Image edited successfully!")

    except Exception as e:
        messages.error(request, f"Error editing image: {str(e)}")

    return redirect('scene_manager', project_pk=project.pk, scene_pk=scene.pk)


@require_POST
def edit_scene_image_ajax(request, project_pk, scene_pk):
    """AJAX endpoint for editing scene images - completely separate from generation."""
    project = get_object_or_404(Project, pk=project_pk)
    scene = get_object_or_404(Scene, pk=scene_pk, project=project)

    try:
        # Only allow editing if image exists
        if not scene.approved_image:
            return JsonResponse({
                'status': 'error',
                'message': 'No image to edit. Please generate an image first.'
            })


        # Get edit prompt from request
        import json
        body = json.loads(request.body)
        edit_prompt = body.get('edit_prompt', '').strip()

        if not edit_prompt:
            return JsonResponse({
                'status': 'error',
                'message': 'Please provide edit instructions'
            })

        generator = ImageGenerator()

        # Edit the image - ONLY pass the current image and edit prompt
        filename_base = f"project_{project.pk}_scene_{scene.pk}_edited"
        image_file = generator.edit_image(
            scene.approved_image.path,
            edit_prompt,
            filename_base,
            project=project,
            scene=scene
        )

        # Save the edited image and the edit prompt
        scene.approved_image = image_file
        scene.edit_prompt = edit_prompt
        scene.save()

        return JsonResponse({
            'status': 'success',
            'message': 'Image edited successfully!',
            'image_url': scene.approved_image.url if scene.approved_image else None
        })

    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Error editing image: {str(e)}'
        })


@require_POST
def generate_character_image_ajax(request, project_pk, character_pk):
    """AJAX endpoint for generating/regenerating character image."""
    project = get_object_or_404(Project, pk=project_pk)
    character = get_object_or_404(Character, pk=character_pk, project=project)

    try:
        # Use generation prompt if available, otherwise use description
        prompt = request.POST.get('prompt', character.generation_prompt or character.description)

        # Update generation prompt if new one provided
        if prompt != character.generation_prompt:
            character.generation_prompt = prompt
            character.save()

        generator = CharacterGenerator()

        # Generate the character image
        image_file = generator.generate_character(
            prompt,
            character.name,
            project_style=project.style,
            project_color_scheme=project.color_scheme,
            project=project,
            character=character
        )

        # Save the generated image
        character.generated_image = image_file
        character.save()

        # Return success with image URL
        response_data = {
            'status': 'success',
            'message': 'Character image generated successfully!',
            'image_url': character.generated_image.url if character.generated_image else None
        }

    except Exception as e:
        response_data = {
            'status': 'error',
            'message': f'Error generating character image: {str(e)}'
        }

    return JsonResponse(response_data)


def character_gallery(request, project_pk):
    """Display all characters in a gallery view."""
    project = get_object_or_404(Project, pk=project_pk)
    characters = project.characters.all()

    context = {
        'project': project,
        'characters': characters
    }
    return render(request, 'stories/character_gallery.html', context)


def generation_settings(request):
    """View for managing image generation cost settings."""
    settings = GenerationSettings.get_settings()

    if request.method == 'POST':
        form = GenerationSettingsForm(request.POST, instance=settings)
        if form.is_valid():
            form.save()
            messages.success(request, 'Generation settings updated successfully!')
            return redirect('generation_settings')
    else:
        form = GenerationSettingsForm(instance=settings)

    # Calculate total costs across all projects
    total_costs = GenerationCost.objects.aggregate(
        total_cost=Sum('cost'),
        total_count=Count('id')
    )

    # Get cost breakdown by type
    cost_by_type = GenerationCost.objects.values('generation_type').annotate(
        count=Count('id'),
        total=Sum('cost')
    ).order_by('-total')

    # Get top 5 most expensive projects
    top_projects = Project.objects.filter(
        total_generation_cost__gt=0
    ).order_by('-total_generation_cost')[:5]

    # Get recent generation history
    recent_generations = GenerationCost.objects.select_related(
        'project', 'scene', 'character'
    ).order_by('-created_at')[:20]

    # Get API key status
    openai_key = settings.get_openai_api_key()
    google_key = settings.get_google_api_key()
    artemox_key = settings.get_artemox_api_key()

    api_key_status = {
        'openai': {
            'is_set': bool(openai_key),
            'source': settings.get_api_key_source('openai'),
            'masked': settings.mask_api_key(openai_key) if openai_key else 'Not configured'
        },
        'google': {
            'is_set': bool(google_key),
            'source': settings.get_api_key_source('google'),
            'masked': settings.mask_api_key(google_key) if google_key else 'Not configured'
        },
        'artemox': {
            'is_set': bool(artemox_key),
            'source': settings.get_api_key_source('artemox'),
            'masked': settings.mask_api_key(artemox_key) if artemox_key else 'Not configured'
        }
    }

    context = {
        'form': form,
        'settings': settings,
        'total_costs': total_costs,
        'cost_by_type': cost_by_type,
        'top_projects': top_projects,
        'recent_generations': recent_generations,
        'currency_symbol': {
            'USD': '$',
            'EUR': '€',
            'GBP': '£'
        }.get(settings.currency, '$'),
        'api_key_status': api_key_status,
        'effective_ai_provider': settings.get_current_provider()
    }

    return render(request, 'stories/generation_settings.html', context)