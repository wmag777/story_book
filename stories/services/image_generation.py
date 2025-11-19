import time
import mimetypes
import re
from google import genai
from google.genai import types
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.cache import cache
from decimal import Decimal


class ImageGenerator:
    def __init__(self):
        # Get API key from GenerationSettings first, fallback to ENV
        from stories.models import GenerationSettings
        gen_settings = GenerationSettings.get_settings()
        self.google_api_key = gen_settings.get_google_api_key()

        if not self.google_api_key:
            raise ValueError(
                "Google API ключ не найден. Пожалуйста, добавьте GOOGLE_API в настройках проекта или в Replit Secrets. "
                "Без ключа генерация изображений невозможна."
            )

    def get_prompt_template(self, template_type: str, **kwargs) -> str:
        """Get prompt template from database with caching.

        Args:
            template_type: Type of template to fetch
            **kwargs: Variables to render in the template

        Returns:
            Rendered template string or empty string if not found
        """
        # Check cache first
        cache_key = f'prompt_template_{template_type}'
        cached_template = cache.get(cache_key)

        # Import here to avoid circular imports
        from stories.models import PromptTemplate

        template_text = None

        if cached_template:
            template_text = cached_template
        else:
            try:
                template = PromptTemplate.objects.get(
                    template_type=template_type,
                    is_active=True
                )
                template_text = template.template_text
                # Cache for 1 hour
                cache.set(cache_key, template_text, 3600)
                print(f"Loaded template '{template_type}' from database: {template_text}")
            except PromptTemplate.DoesNotExist:
                print(f"WARNING: Template '{template_type}' not found in database")
                # Return empty string instead of hardcoded fallback
                return ""

        # If we have kwargs, render the template
        if template_text and kwargs:
            try:
                return template_text.format(**kwargs)
            except KeyError as e:
                print(f"WARNING: Missing variable {e} in template '{template_type}'")
                return template_text

        return template_text or ""

    def replace_character_placeholders(self, prompt, characters, use_references=False, characters_with_images=None):
        """Replace character placeholders with appropriate text

        Args:
            prompt: The prompt with {CharacterName} placeholders
            characters: All characters in the project
            use_references: If True and character has image, use minimal replacement
            characters_with_images: Set of character names that have reference images

        Returns:
            Prompt with placeholders replaced appropriately
        """
        final_prompt = prompt
        characters_with_images = characters_with_images or set()

        for character in characters:
            pattern = re.compile(re.escape(f"{{{character.name}}}"), re.IGNORECASE)

            if use_references and character.name in characters_with_images:
                # When using reference images, just keep the name
                replacement = character.name
            else:
                # When not using references, use full description
                replacement = character.description

            final_prompt = pattern.sub(replacement, final_prompt)

        return final_prompt

    def generate(self, prompt, filename_base, max_retries=3, reference_images=None, project=None, scene=None, character=None):
        """
        Main generation method using Google Nano Banana.

        Args:
            prompt: The text prompt for image generation
            filename_base: Base name for the generated file
            max_retries: Number of retries for failed attempts
            reference_images: List of reference image paths for character consistency

        Returns:
            ContentFile with generated image data
        """
        return self.generate_with_nano_banana(prompt, filename_base, max_retries, reference_images, project, scene, character)

    def generate_with_nano_banana(self, prompt, filename_base, max_retries=3, reference_images=None, project=None, scene=None, character=None):
        """
        Generate image using Google's Gemini model (Nano Banana)

        Args:
            prompt: Text prompt for generation
            filename_base: Base name for output file
            max_retries: Number of retry attempts
            reference_images: List of character reference images for consistency
        """

        # Initialize client with API key
        if not self.google_api_key:
            raise ValueError(
                "Google API ключ не настроен. Добавьте GOOGLE_API в настройках проекта или в Replit Secrets."
            )

        try:
            client = genai.Client(api_key=self.google_api_key)
        except Exception as e:
            raise ValueError(
                f"Ошибка инициализации Google API клиента: {str(e)}. "
                f"Проверьте правильность API ключа."
            )

        model = "gemini-2.5-flash-image-preview"
        retry_delay = 2  # seconds

        for attempt in range(max_retries):
            try:
                # Build content parts
                parts = [types.Part.from_text(text=prompt)]

                # Add reference images if provided
                if reference_images:
                    for ref_image_path in reference_images:
                        try:
                            # Read the image file
                            with open(ref_image_path, 'rb') as f:
                                image_data = f.read()

                            # Add image as Part
                            parts.append(
                                types.Part.from_bytes(
                                    data=image_data,
                                    mime_type='image/jpeg'  # Will be updated based on actual type
                                )
                            )
                        except Exception as e:
                            print(f"Warning: Could not load reference image {ref_image_path}: {e}")

                # Create contents with proper structure
                contents = [
                    types.Content(
                        role="user",
                        parts=parts,
                    ),
                ]

                # Configure generation with both IMAGE and TEXT modalities
                generate_content_config = types.GenerateContentConfig(
                    response_modalities=["IMAGE", "TEXT"],
                    temperature=1.0,
                )

                image_data = None
                mime_type = None
                text_output = []

                # Use streaming
                for chunk in client.models.generate_content_stream(
                    model=model,
                    contents=contents,
                    config=generate_content_config,
                ):
                    # Check if chunk has valid content
                    if (
                        chunk.candidates is None
                        or len(chunk.candidates) == 0
                        or chunk.candidates[0].content is None
                        or chunk.candidates[0].content.parts is None
                    ):
                        continue

                    # Process each part in the chunk
                    for part in chunk.candidates[0].content.parts:
                        # Handle image data
                        if hasattr(part, 'inline_data') and part.inline_data and part.inline_data.data:
                            print(f"Found image data, MIME type: {part.inline_data.mime_type}")
                            image_data = part.inline_data.data
                            mime_type = part.inline_data.mime_type

                        # Handle text data
                        elif hasattr(part, 'text') and part.text:
                            text_output.append(part.text)

                if image_data:
                    # Determine file extension from mime type
                    file_extension = mimetypes.guess_extension(mime_type)
                    if not file_extension:
                        file_extension = ".png"

                    # Track cost if project is provided
                    if project:
                        self._track_generation_cost(
                            project=project,
                            scene=scene,
                            character=character,
                            generation_type='character' if character else 'new',
                            prompt=prompt
                        )

                    # Create a Django ContentFile from the image data
                    filename = f"{filename_base}{file_extension}"
                    return ContentFile(image_data, name=filename)
                else:
                    raise Exception("No image was generated in the response")

            except Exception as e:
                error_msg = str(e)
                print(f"Attempt {attempt + 1}/{max_retries} failed: {error_msg}")

                # Check if it's a 500 internal error
                if "500" in error_msg or "INTERNAL" in error_msg:
                    if attempt < max_retries - 1:
                        print(f"Retrying in {retry_delay} seconds...")
                        time.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff
                        continue

                # If not a 500 error or last attempt, raise exception with Russian message
                if attempt == max_retries - 1:
                    if "quota" in error_msg.lower() or "limit" in error_msg.lower():
                        raise Exception(
                            f"Превышен лимит API запросов. Проверьте квоту вашего Google API ключа. "
                            f"Детали ошибки: {error_msg}"
                        )
                    elif "auth" in error_msg.lower() or "permission" in error_msg.lower():
                        raise Exception(
                            f"Ошибка авторизации API. Проверьте правильность вашего Google API ключа. "
                            f"Детали ошибки: {error_msg}"
                        )
                    elif "invalid" in error_msg.lower() and "key" in error_msg.lower():
                        raise Exception(
                            f"Неверный API ключ Google. Проверьте ключ в настройках проекта. "
                            f"Детали ошибки: {error_msg}"
                        )
                    else:
                        raise Exception(
                            f"Не удалось сгенерировать изображение после {max_retries} попыток. "
                            f"Детали ошибки: {error_msg}"
                        )

        raise Exception("Image generation failed")

    def edit_image(self, current_image_path, edit_prompt, filename_base, max_retries=3, project=None, scene=None):
        """
        Edit an existing image using Google Nano Banana.

        Args:
            current_image_path: Path to the current image to edit
            edit_prompt: Text instructions for editing
            filename_base: Base name for the output file
            max_retries: Number of retry attempts

        Returns:
            ContentFile with edited image data
        """
        return self.edit_with_nano_banana(
            current_image_path, edit_prompt, filename_base,
            max_retries, project, scene
        )

    def edit_with_nano_banana(self, current_image_path, edit_prompt, filename_base,
                              max_retries=3, project=None, scene=None):
        """
        Edit an image using Google's Gemini model.

        Args:
            current_image_path: Path to the current image
            edit_prompt: Instructions for editing
            filename_base: Base name for output
            max_retries: Retry attempts

        Returns:
            ContentFile with edited image
        """
        # Initialize client
        if not self.google_api_key:
            raise ValueError(
                "Google API ключ не настроен. Добавьте GOOGLE_API в настройках проекта или в Replit Secrets."
            )

        try:
            client = genai.Client(api_key=self.google_api_key)
        except Exception as e:
            raise ValueError(
                f"Ошибка инициализации Google API клиента: {str(e)}. "
                f"Проверьте правильность API ключа."
            )

        model = "gemini-2.5-flash-image-preview"
        retry_delay = 2

        for attempt in range(max_retries):
            try:
                # Read the current image
                with open(current_image_path, 'rb') as f:
                    current_image_data = f.read()

                # Build content parts - only the current image and edit prompt
                parts = [
                    types.Part.from_bytes(
                        data=current_image_data,
                        mime_type='image/jpeg'
                    ),
                    types.Part.from_text(text=edit_prompt)
                ]

                # Create content structure
                contents = [
                    types.Content(
                        role="user",
                        parts=parts
                    )
                ]

                # Configure generation
                generate_content_config = types.GenerateContentConfig(
                    response_modalities=["IMAGE", "TEXT"],
                    temperature=0.8,  # Slightly lower for editing to maintain consistency
                )

                # Generate edited image
                image_data = None
                mime_type = None

                for chunk in client.models.generate_content_stream(
                    model=model,
                    contents=contents,
                    config=generate_content_config,
                ):
                    if (
                        chunk.candidates is None
                        or len(chunk.candidates) == 0
                        or chunk.candidates[0].content is None
                        or chunk.candidates[0].content.parts is None
                    ):
                        continue

                    for part in chunk.candidates[0].content.parts:
                        if hasattr(part, 'inline_data') and part.inline_data and part.inline_data.data:
                            print(f"Found edited image, MIME type: {part.inline_data.mime_type}")
                            image_data = part.inline_data.data
                            mime_type = part.inline_data.mime_type

                if image_data:
                    # Track cost if project is provided
                    if project:
                        self._track_generation_cost(
                            project=project,
                            scene=scene,
                            character=None,
                            generation_type='edit',
                            prompt=edit_prompt
                        )

                    # Determine file extension
                    file_extension = mimetypes.guess_extension(mime_type) or ".png"
                    filename = f"{filename_base}_edited{file_extension}"
                    return ContentFile(image_data, name=filename)
                else:
                    raise Exception("No edited image was generated")

            except Exception as e:
                error_msg = str(e)
                print(f"Edit attempt {attempt + 1}/{max_retries} failed: {error_msg}")

                if attempt < max_retries - 1 and ("500" in error_msg or "INTERNAL" in error_msg):
                    print(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    retry_delay *= 2
                    continue

                if attempt == max_retries - 1:
                    if "quota" in error_msg.lower() or "limit" in error_msg.lower():
                        raise Exception(
                            f"Превышен лимит API запросов. Проверьте квоту вашего Google API ключа. "
                            f"Детали ошибки: {error_msg}"
                        )
                    elif "auth" in error_msg.lower() or "permission" in error_msg.lower():
                        raise Exception(
                            f"Ошибка авторизации API. Проверьте правильность вашего Google API ключа. "
                            f"Детали ошибки: {error_msg}"
                        )
                    else:
                        raise Exception(
                            f"Не удалось отредактировать изображение после {max_retries} попыток. "
                            f"Детали ошибки: {error_msg}"
                        )

        raise Exception("Image editing failed")

    def _track_generation_cost(self, project, scene=None, character=None, generation_type='new', prompt=''):
        """Track the cost of an image generation."""
        from stories.models import GenerationSettings, GenerationCost

        # Get current settings
        settings = GenerationSettings.get_settings()

        # Only track if tracking is enabled
        if not settings.is_tracking_enabled:
            return

        # Determine cost based on type
        if generation_type == 'edit':
            cost = settings.cost_per_edit
        else:
            cost = settings.cost_per_generation

        # Create cost record
        generation_cost = GenerationCost.objects.create(
            project=project,
            scene=scene,
            character=character,
            generation_type=generation_type,
            cost=cost,
            currency=settings.currency,
            prompt_preview=prompt[:200] if prompt else ''
        )

        # Update project totals
        project.generation_count += 1
        project.total_generation_cost += cost
        project.save(update_fields=['generation_count', 'total_generation_cost'])