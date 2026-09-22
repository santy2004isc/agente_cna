from abc import ABC, abstractmethod

class BaseLLMService(ABC):
    @abstractmethod
    def generate_response(self, prompt: str, system_instruction: str = "") -> str:
        pass