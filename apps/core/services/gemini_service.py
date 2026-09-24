import time
from google import genai
from google.genai import types
from google.genai.errors import ServerError
from django.conf import settings
from .base_llm import BaseLLMService

class GeminiService(BaseLLMService):
    def __init__(self):
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self.model_name = settings.GEMINI_MODEL

    def generate_response(self, prompt: str, system_instruction: str = "", max_retries: int = 3) -> str:
        config = None
        if system_instruction:
            config = types.GenerateContentConfig(system_instruction=system_instruction)

        # Lógica de reintentos con espera exponencial (Exponential Backoff)
        for attempt in range(max_retries):
            try:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=config,
                )
                return response.text
            except ServerError as e:
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Espera 1s, luego 2s, etc.
                    continue
                raise e