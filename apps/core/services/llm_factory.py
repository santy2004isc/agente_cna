from django.conf import settings
from .gemini_service import GeminiService
from .groq_service import GroqService

def get_llm_service():
    provider = settings.DEFAULT_LLM_PROVIDER.lower()
    if provider == 'gemini':
        return GeminiService()
    elif provider == 'groq':
        return GroqService()
    else:
        raise ValueError(f"Proveedor de LLM no soportado: {provider}")