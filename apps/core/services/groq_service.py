from groq import Groq
from django.conf import settings
from .base_llm import BaseLLMService

class GroqService(BaseLLMService):
    def __init__(self):
        self.client = Groq(api_key=settings.GROQ_API_KEY)
        self.model_name = settings.GROQ_MODEL

    def generate_response(self, prompt: str, system_instruction: str = "", max_tokens: int = 750) -> str:
        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})

        response = self.client.chat.completions.create(
            messages=messages,
            model=self.model_name,
            max_tokens=max_tokens,  # <-- Limita la reserva de tokens para respetar la cuota
        )
        return response.choices[0].message.content