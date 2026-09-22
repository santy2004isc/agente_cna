import google.generativeai as genai
from django.conf import settings
from .base_llm import BaseLLMService

class GeminiService(BaseLLMService):
    def __init__(self):
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = genai.GenerativeModel('gemini-1.5-flash')

    def generate_response(self, prompt: str, system_instruction: str = "") -> str:
        full_prompt = f"{system_instruction}\n\nPregunta: {prompt}" if system_instruction else prompt
        response = self.model.generate_content(full_prompt)
        return response.text