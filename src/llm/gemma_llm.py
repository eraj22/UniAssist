import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from llm.base_llm import BaseLLM

class GemmaLLM(BaseLLM):
    def __init__(self, model_name="google/gemma-2b-it"):
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype=torch.float16,
            device_map="auto"
        )

    def generate(self, prompt: str) -> str:
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)

        outputs = self.model.generate(
            **inputs,
            max_new_tokens=256,
            temperature=0.7,
            do_sample=True
        )

        return self.tokenizer.decode(outputs[0], skip_special_tokens=True)
