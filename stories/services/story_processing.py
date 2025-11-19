from typing import List
from pydantic import BaseModel
from SimplerLLM.language.llm import LLM, LLMProvider
from SimplerLLM.language.llm_addons import generate_pydantic_json_model
from django.conf import settings
from django.core.cache import cache


class Scenes(BaseModel):
    scenes: List[str]


class CharacterModel(BaseModel):
    name: str
    description: str


class Characters(BaseModel):
    characters: List[CharacterModel]


class StoryProcessor:
    def __init__(self):
        # Get API key from GenerationSettings first, fallback to ENV
        from stories.models import GenerationSettings
        gen_settings = GenerationSettings.get_settings()
        api_key = gen_settings.get_openai_api_key()

        self.llm_instance = LLM.create(
            provider=LLMProvider.OPENAI,
            model_name="gpt-4o",
            api_key=api_key
        )
        self._prompt_cache = {}

    def get_prompt_template(self, template_type: str) -> str:
        """Get prompt template from database with caching."""
        # Check cache first
        cache_key = f'prompt_template_{template_type}'
        cached_prompt = cache.get(cache_key)
        if cached_prompt:
            return cached_prompt

        # Import here to avoid circular imports
        from stories.models import PromptTemplate

        try:
            template = PromptTemplate.objects.get(
                template_type=template_type,
                is_active=True
            )
            prompt_text = template.template_text
            # Cache for 1 hour
            cache.set(cache_key, prompt_text, 3600)
            return prompt_text
        except PromptTemplate.DoesNotExist:
            # Log warning and return empty string - templates should be in database
            print(f"WARNING: Template '{template_type}' not found in database. Please ensure prompt templates are properly initialized.")
            return ""

    def extract_scenes(self, story: str) -> List[str]:
        prompt_template = self.get_prompt_template('scene_extraction')
        prompt = prompt_template.format(story=story)
        result = generate_pydantic_json_model(
            model_class=Scenes,
            llm_instance=self.llm_instance,
            prompt=prompt
        )
        return result.scenes

    def extract_characters(self, story: str) -> List[CharacterModel]:
        prompt_template = self.get_prompt_template('character_extraction')
        prompt = prompt_template.format(story=story)
        result = generate_pydantic_json_model(
            model_class=Characters,
            llm_instance=self.llm_instance,
            prompt=prompt
        )
        return result.characters

    @staticmethod
    def clear_prompt_cache():
        """Clear cached prompt templates."""
        cache.delete_many([
            'prompt_template_scene_extraction',
            'prompt_template_character_extraction'
        ])