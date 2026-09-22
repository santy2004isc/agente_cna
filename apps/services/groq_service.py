from groq import Groq
from django.conf import settings
from .base_llm import BaseLLMService

class GroqService(BaseLLMService):
    def __init__(self):
        self.client = Groq(api_key=settings.GROQ_API_KEY)
        self.model_name = "llama-3.1-70b-versatile"

    def generate_response(self, prompt: str, system_instruction: str = "") -> str:
        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})

        response = self.client.chat.completions.create(
            messages=messages,
            model=self.model_name,
        )
        return response.choices[0].message.content