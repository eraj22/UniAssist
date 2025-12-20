import requests
from llm.base_llm import BaseLLM

class OllamaLLM(BaseLLM):
    def __init__(self, model_name="llama3.2:1b", ollama_url="http://localhost:11434"):
        self.model_name = model_name
        self.api_endpoint = f"{ollama_url}/api/generate"

    def generate(self, prompt: str) -> str:
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False
        }

        try:
            response = requests.post(self.api_endpoint, json=payload, timeout=180)
            if response.status_code == 200:
                return response.json().get("response", "")
            return f"Error: {response.status_code}"
        except Exception as e:
            return f"Ollama error: {str(e)}"
