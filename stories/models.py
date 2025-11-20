from django.db import models
from django.contrib.auth.models import User
import json
import os
from decimal import Decimal


class Project(models.Model):
    name = models.CharField(max_length=200)
    style = models.CharField(max_length=100, default='Ghibli-style')
    color_scheme = models.CharField(max_length=50, default='colored')
    total_generation_cost = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        default=Decimal('0.0000'),
        help_text="Total cost of all image generations for this project"
    )
    generation_count = models.IntegerField(
        default=0,
        help_text="Total number of image generations for this project"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['-updated_at']


class Character(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='characters')
    name = models.CharField(max_length=100)
    description = models.TextField()
    generation_prompt = models.TextField(
        null=True,
        blank=True,
        help_text="The prompt used to generate this character's image"
    )
    generated_image = models.ImageField(
        upload_to='character_images/',
        null=True,
        blank=True,
        help_text="AI-generated image of the character"
    )
    reference_image = models.ImageField(
        upload_to='character_references/',
        null=True,
        blank=True,
        help_text="Reference image for character consistency"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.project.name})"

    class Meta:
        ordering = ['name']


class Scene(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='scenes')
    name = models.CharField(max_length=200)
    prompt = models.TextField()
    order = models.IntegerField(default=0)
    approved_image = models.ImageField(upload_to='generated_images/', null=True, blank=True)
    final_prompt = models.TextField(
        null=True,
        blank=True,
        help_text="Custom final prompt to use for generation (overrides auto-generated prompt)"
    )
    use_custom_prompt = models.BooleanField(
        default=False,
        help_text="Whether to use the custom final prompt instead of auto-generating"
    )
    characters = models.ManyToManyField(
        Character,
        blank=True,
        related_name='scenes',
        help_text="Characters that appear in this scene"
    )
    edit_prompt = models.TextField(
        null=True,
        blank=True,
        help_text="Last edit instructions used (e.g., 'Make it sunset', 'Add rain')"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.project.name})"

    class Meta:
        ordering = ['order', 'created_at']

    def save(self, *args, **kwargs):
        if not self.order:
            last_scene = Scene.objects.filter(project=self.project).order_by('-order').first()
            if last_scene:
                self.order = last_scene.order + 1
            else:
                self.order = 1
        super().save(*args, **kwargs)


class PromptTemplate(models.Model):
    TEMPLATE_TYPES = [
        ('scene_extraction', 'Scene Extraction'),
        ('character_extraction', 'Character Extraction'),
        ('image_style_suffix', 'Image Style Suffix'),
        ('reference_image_instruction', 'Reference Image Instruction'),
    ]

    name = models.CharField(max_length=200, help_text="Descriptive name for this template")
    template_type = models.CharField(
        max_length=50,
        choices=TEMPLATE_TYPES,
        unique=True,
        help_text="Type of prompt template"
    )
    template_text = models.TextField(
        help_text="The prompt template text. Use {variable} for placeholders."
    )
    description = models.TextField(
        help_text="Explain what this prompt does and how to use it"
    )
    variables = models.JSONField(
        default=list,
        blank=True,
        help_text="List of variables used in this template (e.g., ['story', 'style'])"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this template is currently active"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.get_template_type_display()})"

    class Meta:
        ordering = ['template_type', 'name']
        verbose_name = "Prompt Template"
        verbose_name_plural = "Prompt Templates"

    def get_variables_from_template(self):
        """Extract variables from template text."""
        import re
        # Find all {variable_name} patterns
        pattern = r'\{([^}]+)\}'
        matches = re.findall(pattern, self.template_text)
        return list(set(matches))

    def save(self, *args, **kwargs):
        """Auto-detect variables before saving."""
        if not self.variables:
            self.variables = self.get_variables_from_template()
        super().save(*args, **kwargs)

    def render(self, **kwargs):
        """Render the template with given variables."""
        try:
            return self.template_text.format(**kwargs)
        except KeyError as e:
            raise ValueError(f"Missing required variable: {e}")

    @classmethod
    def get_default_templates(cls):
        """Return default templates for initial setup."""
        return [
            {
                'name': 'Story Scene Extraction',
                'template_type': 'scene_extraction',
                'template_text': """Extract the main scenes of the [STORY] focusing on what could be turned into an image for the book. [STORY]: {story}""",
                'description': 'Extracts visual scenes from a story that can be illustrated',
                'variables': ['story']
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
                'variables': ['story']
            },
            {
                'name': 'Image Style Suffix',
                'template_type': 'image_style_suffix',
                'template_text': ' Draw in {style} with {color_scheme} colors.',
                'description': 'Added to image prompts to specify artistic style and color scheme',
                'variables': ['style', 'color_scheme']
            },
            {
                'name': 'Reference Image Instruction - Single',
                'template_type': 'reference_image_instruction',
                'template_text': ' Use the exact appearance of {character_name} from the provided reference image.',
                'description': 'Instruction for using character reference images in generation',
                'variables': ['character_name']
            }
        ]


class GenerationSettings(models.Model):
    """Singleton model for storing image generation cost settings"""

    CURRENCY_CHOICES = [
        ('USD', 'US Dollar'),
        ('EUR', 'Euro'),
        ('GBP', 'British Pound'),
    ]

    cost_per_generation = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        default=Decimal('0.0390'),
        help_text="Cost per image generation (default: $0.039 for Gemini 2.5 Flash Image)"
    )
    cost_per_edit = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        default=Decimal('0.0390'),
        help_text="Cost per image edit (default: $0.039 for Gemini 2.5 Flash Image)"
    )
    currency = models.CharField(
        max_length=3,
        choices=CURRENCY_CHOICES,
        default='USD',
        help_text="Currency for cost tracking"
    )
    is_tracking_enabled = models.BooleanField(
        default=True,
        help_text="Enable/disable cost tracking"
    )
    openai_api_key = models.CharField(
        max_length=255,
        blank=True,
        default='',
        help_text="OpenAI API key (overrides environment variable if set)"
    )
    google_api_key = models.CharField(
        max_length=255,
        blank=True,
        default='',
        help_text="Google Gemini API key (overrides environment variable if set)"
    )
    artemox_api_key = models.CharField(
        max_length=255,
        blank=True,
        default='',
        help_text="Artemox API key (overrides environment variable if set)"
    )
    artemox_base_url = models.CharField(
        max_length=255,
        blank=True,
        default='',
        help_text="Artemox Base URL (overrides environment variable if set)"
    )
    ai_provider = models.CharField(
        max_length=20,
        choices=[
            ('openai', 'OpenAI'),
            ('artemox', 'Artemox'),
        ],
        default='openai',
        help_text="Select which AI provider to use for text generation"
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Generation Settings"
        verbose_name_plural = "Generation Settings"

    def __str__(self):
        return f"Image Generation Settings ({self.currency})"

    @classmethod
    def get_settings(cls):
        """Get or create the singleton settings instance"""
        settings, created = cls.objects.get_or_create(pk=1)
        return settings

    def get_openai_api_key(self):
        """Get OpenAI API key from DB or fallback to ENV"""
        if self.openai_api_key:
            return self.openai_api_key
        from django.conf import settings as django_settings
        return django_settings.OPENAI_KEY or ''

    def get_google_api_key(self):
        """Get Google API key from DB or fallback to ENV"""
        if self.google_api_key:
            return self.google_api_key
        from django.conf import settings as django_settings
        return django_settings.GOOGLE_API or ''

    def mask_api_key(self, key):
        """Mask API key showing only last 4 characters"""
        if not key:
            return ''
        if len(key) <= 8:
            return '*' * len(key)
        return '*' * (len(key) - 4) + key[-4:]

    def get_artemox_api_key(self):
        """Get Artemox API key from DB or fallback to ENV"""
        if self.artemox_api_key:
            return self.artemox_api_key
        return os.getenv('ARTEMOX_API_KEY', '')

    def get_artemox_base_url(self):
        """Get Artemox Base URL from DB or fallback to ENV"""
        if self.artemox_base_url:
            return self.artemox_base_url
        return os.getenv('ARTEMOX_BASE_URL', '')

    def has_openai_credentials(self):
        """Check if OpenAI credentials are available from DB or ENV."""
        return bool(self.get_openai_api_key())

    def has_artemox_credentials(self):
        """Check if Artemox credentials are available from DB or ENV."""
        return bool(self.get_artemox_api_key())

    def get_effective_ai_provider(self):
        """
        Determine which provider should be used, preferring Artemox when OpenAI
        credentials отсутствуют, но Artemox доступен.
        """
        openai_key = self.get_openai_api_key()
        artemox_key = self.get_artemox_api_key()

        if self.ai_provider == 'artemox':
            if artemox_key:
                return 'artemox'
            if openai_key:
                return 'openai'

        if self.ai_provider == 'openai':
            if openai_key:
                return 'openai'
            if artemox_key:
                return 'artemox'

        if artemox_key and not openai_key:
            return 'artemox'

        return 'openai'

    def get_current_provider(self):
        """Public helper to expose the effective provider."""
        return self.get_effective_ai_provider()

    def get_current_api_key(self):
        """Get API key for the effective provider with env-based fallback."""
        provider = self.get_effective_ai_provider()
        if provider == 'artemox':
            return self.get_artemox_api_key()
        return self.get_openai_api_key()

    def get_current_base_url(self):
        """Get Base URL based on effective AI provider"""
        provider = self.get_effective_ai_provider()
        if provider == 'artemox':
            return self.get_artemox_base_url()
        return None

    def mask_api_key(self, key):
        """Mask API key showing only last 4 characters"""
        if not key:
            return ''
        if len(key) <= 8:
            return '*' * len(key)
        return '*' * (len(key) - 4) + key[-4:]

    def get_api_key_source(self, key_type):
        """Check if API key is from DB or ENV"""
        if key_type == 'openai':
            return 'Database' if self.openai_api_key else 'Environment'
        elif key_type == 'google':
            return 'Database' if self.google_api_key else 'Environment'
        elif key_type == 'artemox':
            return 'Database' if self.artemox_api_key else 'Environment'
        return 'Unknown'


class GenerationCost(models.Model):
    """Track individual generation costs"""

    GENERATION_TYPES = [
        ('new', 'New Generation'),
        ('edit', 'Edit'),
        ('character', 'Character Generation'),
    ]

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='generation_costs'
    )
    scene = models.ForeignKey(
        Scene,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='generation_costs'
    )
    character = models.ForeignKey(
        Character,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='generation_costs'
    )
    generation_type = models.CharField(
        max_length=20,
        choices=GENERATION_TYPES,
        help_text="Type of generation"
    )
    cost = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        help_text="Cost of this generation"
    )
    currency = models.CharField(
        max_length=3,
        default='USD',
        help_text="Currency used for this cost"
    )
    prompt_preview = models.TextField(
        null=True,
        blank=True,
        help_text="Preview of the prompt used (first 200 chars)"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Generation Cost"
        verbose_name_plural = "Generation Costs"

    def __str__(self):
        return f"{self.project.name} - {self.get_generation_type_display()} - {self.currency}{self.cost}"
