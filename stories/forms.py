from django import forms
from .models import PromptTemplate, Character, GenerationSettings
from decimal import Decimal
import json


class PromptTemplateForm(forms.ModelForm):
    """Form for editing prompt templates."""

    class Meta:
        model = PromptTemplate
        fields = ['name', 'template_text', 'description', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter a descriptive name'
            }),
            'template_text': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 10,
                'placeholder': 'Enter your prompt template. Use {variable_name} for placeholders.',
                'style': 'font-family: monospace;'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Explain what this prompt does'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }

    def clean_template_text(self):
        """Validate template text and extract variables."""
        template_text = self.cleaned_data['template_text']

        # Try to extract variables to ensure valid format
        import re
        pattern = r'\{([^}]+)\}'
        matches = re.findall(pattern, template_text)

        # Store variables for later use
        self.extracted_variables = list(set(matches))

        return template_text

    def save(self, commit=True):
        """Save the form and update variables."""
        instance = super().save(commit=False)

        # Update variables from extracted list
        if hasattr(self, 'extracted_variables'):
            instance.variables = self.extracted_variables

        if commit:
            instance.save()

        # Clear cache when template is updated
        from django.core.cache import cache
        cache_key = f'prompt_template_{instance.template_type}'
        cache.delete(cache_key)

        return instance


class PromptTestForm(forms.Form):
    """Form for testing prompt templates with sample data."""

    test_data = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 5,
            'placeholder': 'Enter test data as JSON, e.g., {"story": "Once upon a time...", "style": "watercolor"}'
        }),
        help_text='Enter test data as JSON to preview the rendered prompt'
    )

    def clean_test_data(self):
        """Validate and parse JSON test data."""
        test_data_str = self.cleaned_data['test_data']

        try:
            test_data = json.loads(test_data_str)
            if not isinstance(test_data, dict):
                raise forms.ValidationError('Test data must be a JSON object')
        except json.JSONDecodeError as e:
            raise forms.ValidationError(f'Invalid JSON: {str(e)}')

        return test_data


class CharacterEditForm(forms.ModelForm):
    """Form for editing character with manual image upload option."""

    manual_image = forms.ImageField(
        required=False,
        label='Upload Character Image',
        help_text='Upload your own character image (JPG, PNG, GIF, or WebP)',
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': 'image/jpeg,image/jpg,image/png,image/gif,image/webp'
        })
    )

    class Meta:
        model = Character
        fields = ['name', 'description', 'generation_prompt']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'required': True
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'required': True
            }),
            'generation_prompt': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Enter a detailed prompt for AI image generation'
            })
        }

    def clean_manual_image(self):
        """Validate uploaded image."""
        image = self.cleaned_data.get('manual_image')
        if image:
            # Check file size (limit to 10MB)
            if image.size > 10 * 1024 * 1024:
                raise forms.ValidationError('Image file size must be under 10MB')

            # Check file extension
            import os
            ext = os.path.splitext(image.name)[1].lower()
            valid_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
            if ext not in valid_extensions:
                raise forms.ValidationError(f'Unsupported file extension. Use: {", ".join(valid_extensions)}')

        return image


class GenerationSettingsForm(forms.ModelForm):
    """Form for configuring image generation cost settings."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Don't render actual API keys in the form for security
        # Instead show placeholder if keys are set
        if self.instance and self.instance.pk:
            if self.instance.openai_api_key:
                self.fields['openai_api_key'].widget.render_value = False
                self.fields['openai_api_key'].widget.attrs['placeholder'] = f"Current: {self.instance.mask_api_key(self.instance.openai_api_key)}"
            if self.instance.google_api_key:
                self.fields['google_api_key'].widget.render_value = False
                self.fields['google_api_key'].widget.attrs['placeholder'] = f"Current: {self.instance.mask_api_key(self.instance.google_api_key)}"

    class Meta:
        model = GenerationSettings
        fields = ['cost_per_generation', 'cost_per_edit', 'currency', 'is_tracking_enabled', 'openai_api_key', 'google_api_key']
        widgets = {
            'cost_per_generation': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.0001',
                'min': '0',
                'placeholder': '0.0390'
            }),
            'cost_per_edit': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.0001',
                'min': '0',
                'placeholder': '0.0390'
            }),
            'currency': forms.Select(attrs={
                'class': 'form-control'
            }),
            'is_tracking_enabled': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'openai_api_key': forms.PasswordInput(attrs={
                'class': 'form-control',
                'placeholder': 'Leave empty to use environment variable'
            }),
            'google_api_key': forms.PasswordInput(attrs={
                'class': 'form-control',
                'placeholder': 'Leave empty to use environment variable'
            })
        }
        labels = {
            'cost_per_generation': 'Cost per New Image Generation',
            'cost_per_edit': 'Cost per Image Edit',
            'currency': 'Currency',
            'is_tracking_enabled': 'Enable Cost Tracking',
            'openai_api_key': 'OpenAI API Key',
            'google_api_key': 'Google Gemini API Key'
        }
        help_texts = {
            'cost_per_generation': 'Current Gemini 2.5 Flash Image price: $0.039 per image',
            'cost_per_edit': 'Current Gemini 2.5 Flash Image price: $0.039 per edit',
            'currency': 'Currency for all cost calculations',
            'is_tracking_enabled': 'Turn on/off cost tracking for all projects',
            'openai_api_key': 'If set, overrides OPENAI_KEY environment variable',
            'google_api_key': 'If set, overrides GOOGLE_API environment variable'
        }

    def clean_cost_per_generation(self):
        """Validate cost per generation."""
        cost = self.cleaned_data.get('cost_per_generation')
        if cost and cost < 0:
            raise forms.ValidationError('Cost cannot be negative')
        return cost

    def clean_cost_per_edit(self):
        """Validate cost per edit."""
        cost = self.cleaned_data.get('cost_per_edit')
        if cost and cost < 0:
            raise forms.ValidationError('Cost cannot be negative')
        return cost

    def save(self, commit=True):
        """Save form while preserving existing API keys if not changed."""
        instance = super().save(commit=False)

        # Only update API keys if new values are provided
        if not self.cleaned_data.get('openai_api_key'):
            # Preserve existing key if no new value provided
            instance.openai_api_key = self.instance.openai_api_key if self.instance.pk else ''

        if not self.cleaned_data.get('google_api_key'):
            # Preserve existing key if no new value provided
            instance.google_api_key = self.instance.google_api_key if self.instance.pk else ''

        if commit:
            instance.save()

        return instance