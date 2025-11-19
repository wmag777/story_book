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
        # Получить API ключ сначала из GenerationSettings, затем из переменных окружения
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
        """Получить шаблон промпта из базы данных с кэшированием."""
        # Сначала проверить кэш
        cache_key = f'prompt_template_{template_type}'
        cached_prompt = cache.get(cache_key)
        if cached_prompt:
            return cached_prompt

        # Импорт здесь, чтобы избежать циклических импортов
        from stories.models import PromptTemplate

        try:
            template = PromptTemplate.objects.get(
                template_type=template_type,
                is_active=True
            )
            prompt_text = template.template_text
            # Кэшировать на 1 час
            cache.set(cache_key, prompt_text, 3600)
            return prompt_text
        except PromptTemplate.DoesNotExist:
            # Записать предупреждение и вернуть пустую строку - шаблоны должны быть в базе данных
            print(f"ПРЕДУПРЕЖДЕНИЕ: Шаблон '{template_type}' не найден в базе данных. Пожалуйста, убедитесь, что промпт-шаблоны правильно инициализированы.")
            return ""

    def extract_scenes(self, story: str) -> List[str]:
        prompt_template = self.get_prompt_template('scene_extraction')

        if not prompt_template:
            raise ValueError("Шаблон извлечения сцен не найден в базе данных. Пожалуйста, убедитесь, что промпт-шаблоны инициализированы.")

        prompt = prompt_template.format(story=story)
        result = generate_pydantic_json_model(
            model_class=Scenes,
            llm_instance=self.llm_instance,
            prompt=prompt
        )

        if isinstance(result, str):
            raise ValueError(f"Не удалось извлечь сцены. API вернул неожиданный ответ: {result[:200]}")

        if not hasattr(result, 'scenes'):
            raise ValueError(f"Не удалось извлечь сцены. Результат не имеет атрибута 'scenes'. Тип: {type(result)}")

        return result.scenes

    def extract_characters(self, story: str) -> List[CharacterModel]:
        prompt_template = self.get_prompt_template('character_extraction')

        if not prompt_template:
            raise ValueError("Шаблон извлечения персонажей не найден в базе данных. Пожалуйста, убедитесь, что промпт-шаблоны инициализированы.")

        prompt = prompt_template.format(story=story)
        result = generate_pydantic_json_model(
            model_class=Characters,
            llm_instance=self.llm_instance,
            prompt=prompt
        )

        if isinstance(result, str):
            raise ValueError(f"Не удалось извлечь персонажей. API вернул неожиданный ответ: {result[:200]}")

        if not hasattr(result, 'characters'):
            raise ValueError(f"Не удалось извлечь персонажей. Результат не имеет атрибута 'characters'. Тип: {type(result)}")

        return result.characters

    @staticmethod
    def clear_prompt_cache():
        """Очистить кэшированные промпт-шаблоны."""
        cache.delete_many([
            'prompt_template_scene_extraction',
            'prompt_template_character_extraction'
        ])