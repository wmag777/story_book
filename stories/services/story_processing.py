import os
from typing import List, Optional
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


ORIGINAL_OPENAI_BASE_URL = os.environ.get('OPENAI_BASE_URL')


class StoryProcessor:
    def __init__(self):
        # Получить API ключ сначала из GenerationSettings, затем из переменных окружения
        from stories.models import GenerationSettings
        gen_settings = GenerationSettings.get_settings()
        ai_provider = gen_settings.get_current_provider()
        api_key = gen_settings.get_current_api_key()
        base_url = gen_settings.get_current_base_url()
        self._configure_openai_base_url(ai_provider, base_url)
        
        print("=== DEBUG StoryProcessor INIT ===")
        print(f"Выбран AI провайдер: {ai_provider}")
        print(f"API Key получен: {'ДА' if api_key else 'НЕТ'}")
        if api_key:
            print(f"Длина API ключа: {len(api_key)}")
            print(f"Префикс API ключа: {api_key[:15]}...")
        if base_url:
            print(f"Используется кастомный base_url: {base_url}")
        
        if not api_key:
            raise ValueError("API ключ не найден ни для OpenAI, ни для Artemox. Укажите креды в .env или в GenerationSettings.")
        
        provider_enum = getattr(LLMProvider, ai_provider.upper(), LLMProvider.OPENAI)
        model_name = getattr(
            settings,
            'ARTEMOX_MODEL_NAME' if ai_provider == 'artemox' else 'OPENAI_MODEL_NAME',
            'gpt-4o' if ai_provider == 'openai' else 'gpt-4o-mini'
        )
        llm_kwargs = {
            'provider': provider_enum,
            'model_name': model_name,
            'api_key': api_key
        }

        try:
            self.llm_instance = LLM.create(**llm_kwargs)
            print("LLM instance создан успешно")
        except Exception as e:
            print(f"Ошибка создания LLM instance: {e}")
            raise
        
        self._prompt_cache = {}
        print("=== DEBUG StoryProcessor INIT COMPLETED ===")

    def _configure_openai_base_url(self, ai_provider: str, base_url: Optional[str]):
        """
        Artemox использует OpenAI-совместимый API. Пакет SimplerLLM не умеет передавать кастомный
        base_url напрямую, поэтому подменяем переменную окружения OPENAI_BASE_URL на время работы.
        """
        default_base_url = ORIGINAL_OPENAI_BASE_URL
        if ai_provider == 'artemox':
            if not base_url:
                raise ValueError("Для Artemox необходимо указать base_url (например, https://api.artemox.com/v1)")
            os.environ['OPENAI_BASE_URL'] = base_url
        else:
            if default_base_url:
                os.environ['OPENAI_BASE_URL'] = default_base_url
            else:
                os.environ.pop('OPENAI_BASE_URL', None)

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
        print("=== DEBUG extract_scenes ===")
        print(f"1. Получение шаблона для извлечения сцен...")
        
        prompt_template = self.get_prompt_template('scene_extraction')
        print(f"2. Шаблон получен: {'ДА' if prompt_template else 'НЕТ'}")
        print(f"3. Длина шаблона: {len(prompt_template) if prompt_template else 0}")

        if not prompt_template:
            raise ValueError("Шаблон извлечения сцен не найден в базе данных. Пожалуйста, убедитесь, что промпт-шаблоны инициализированы.")

        print(f"4. Длина исходной истории: {len(story)} символов")
        print(f"5. Первые 200 символов истории: {story[:200]}...")
        
        prompt = prompt_template.format(story=story)
        print(f"6. Длина полного промпта: {len(prompt)} символов")
        print(f"7. Первые 300 символов промпта: {prompt[:300]}...")
        
        print(f"8. Вызов generate_pydantic_json_model...")
        try:
            result = generate_pydantic_json_model(
                model_class=Scenes,
                llm_instance=self.llm_instance,
                prompt=prompt
            )
            
            print(f"9. Успешный вызов API")
            print(f"10. Тип результата: {type(result)}")
            print(f"11. Результат: {result}")
            
            if isinstance(result, str):
                print(f"12. ОШИБКА: Результат является строкой вместо объекта")
                print(f"13. Содержимое строки: {result}")
                print(f"14. Первые 500 символов ответа: {result[:500]}")
                raise ValueError(f"Не удалось извлечь сцены. API вернул неожиданный ответ: {result[:200]}")
            
            if not hasattr(result, 'scenes'):
                print(f"15. ОШИБКА: Результат не имеет атрибута 'scenes'")
                print(f"16. Доступные атрибуты: {dir(result)}")
                print(f"17. Содержимое результата: {result}")
                raise ValueError(f"Не удалось извлечь сцены. Результат не имеет атрибута 'scenes'. Тип: {type(result)}")
            
            print(f"18. Успешно извлечено сцен: {len(result.scenes)}")
            print(f"19. Сцены: {result.scenes}")
            print("=== DEBUG extract_scenes COMPLETED ===")
            
            return result.scenes
            
        except Exception as e:
            print(f"20. ИСКЛЮЧЕНИЕ в extract_scenes: {str(e)}")
            print(f"21. Тип исключения: {type(e).__name__}")
            import traceback
            print(f"22. Traceback: {traceback.format_exc()}")
            print("=== DEBUG extract_scenes FAILED ===")
            raise

    def extract_characters(self, story: str) -> List[CharacterModel]:
        prompt_template = self.get_prompt_template('character_extraction')

        if not prompt_template:
            raise ValueError("Шаблон извлечения персонажей не найден в базе данных.")

        print(f"Prompt template: {prompt_template}")  # Логируем шаблон
        print(f"Story length: {len(story)}")  # Логируем длину истории
        
        prompt = prompt_template.format(story=story)
        print(f"Full prompt: {prompt[:500]}...")  # Логируем начало промпта
        
        try:
            result = generate_pydantic_json_model(
                model_class=Characters,
                llm_instance=self.llm_instance,
                prompt=prompt
            )
            
            print(f"Result type: {type(result)}")  # Логируем тип результата
            print(f"Result: {result}")  # Логируем полный результат
            
            if isinstance(result, str):
                print(f"Raw API response: {result}")  # Логируем сырой ответ
                raise ValueError(f"Не удалось извлечь персонажей. API вернул неожиданный ответ: {result[:200]}")
            
            if not hasattr(result, 'characters'):
                raise ValueError(f"Результат не имеет атрибута 'characters'. Полный ответ: {result}")
            
            return result.characters
            
        except Exception as e:
            print(f"Error in extract_characters: {str(e)}")
            print(f"Error type: {type(e)}")
            raise


    def test_openai_connection(self):
        """Тестирование подключения к OpenAI"""
        print("=== TESTING OPENAI CONNECTION ===")
        try:
            # Простой тестовый запрос
            test_prompt = "Ответь одним словом: 'тест'"
            print(f"Тестовый промпт: {test_prompt}")
            
            test_response = self.llm_instance.generate_response(test_prompt)
            print(f"Тестовый ответ: {test_response}")
            print("=== OPENAI CONNECTION TEST: SUCCESS ===")
            return True
        except Exception as e:
            print(f"Ошибка подключения к OpenAI: {e}")
            print(f"Тип ошибки: {type(e).__name__}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            print("=== OPENAI CONNECTION TEST: FAILED ===")
            return False    
        

    @staticmethod
    def clear_prompt_cache():
        """Очистить кэшированные промпт-шаблоны."""
        cache.delete_many([
            'prompt_template_scene_extraction',
            'prompt_template_character_extraction'
        ])