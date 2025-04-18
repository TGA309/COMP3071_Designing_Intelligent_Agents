from abc import ABC, abstractmethod
import os
from typing import Optional
import torch
from transformers import AutoTokenizer, BitsAndBytesConfig
from transformers import Gemma3ForCausalLM

class LLMBase(ABC):
    """Base abstract class for LLM processing pipeline components."""
    
    def __init__(self, model_name: str = None):
        self.model_name = model_name
        self.model, self.tokenizer = self._initialize_model()
    
    @abstractmethod
    def _initialize_model(self):
        pass
    
    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> str:
        pass
    
    @abstractmethod
    def test_connection(self) -> bool:
        pass

class HuggingFaceLLM(LLMBase):
    """Implementation using Gemma3ForCausalLM with proper text-only handling"""
    
    def __init__(self,
                 model_name: str = "gghfez/gemma-3-4b-novision",
                 max_new_tokens: int = 512,
                 load_in_8bit: bool = True,
                 device_map: str = "auto",
                 cache_dir: Optional[str] = None):
        self.max_new_tokens = max_new_tokens
        self.load_in_8bit = load_in_8bit
        self.device_map = device_map
        self.cache_dir = cache_dir or os.path.join(".cache", "huggingface")
        super().__init__(model_name)

    def _initialize_model(self):
        try:
            print(f"Loading model {self.model_name}...")
            
            # Create cache directory
            os.makedirs(self.cache_dir, exist_ok=True)
            
            # Configure quantization
            quantization_config = BitsAndBytesConfig(load_in_8bit=True) if self.load_in_8bit else None
            
            # Load tokenizer
            tokenizer = AutoTokenizer.from_pretrained(
                self.model_name,
                cache_dir=self.cache_dir
            )
            
            # Load model with proper configuration
            model = Gemma3ForCausalLM.from_pretrained(
                self.model_name,
                quantization_config=quantization_config,
                device_map=self.device_map,
                cache_dir=self.cache_dir
            ).eval()
            
            # Configure tokenizer
            if tokenizer.pad_token is None:
                tokenizer.pad_token = tokenizer.eos_token
                
            print(f"Model {self.model_name} loaded successfully")
            return model, tokenizer
            
        except Exception as e:
            raise RuntimeError(f"Error loading model: {str(e)}")

    def generate(self, prompt: str, **kwargs) -> str:
        try:
            # Tokenize input directly
            inputs = self.tokenizer(
                prompt,
                return_tensors="pt",
                return_attention_mask=True
            ).to(self.model.device)
            
            # Set generation parameters
            gen_kwargs = {
                "max_new_tokens": kwargs.get("max_new_tokens", self.max_new_tokens),
                # "temperature": kwargs.get("temperature", 0.7),
                # "top_p": kwargs.get("top_p", 0.95),
                "do_sample": kwargs.get("do_sample", True),
                "pad_token_id": self.tokenizer.pad_token_id
            }
            
            # Generate response
            with torch.inference_mode():
                outputs = self.model.generate(
                    input_ids=inputs.input_ids,
                    attention_mask=inputs.attention_mask,
                    **gen_kwargs
                )
            
            # Decode output
            return self.tokenizer.decode(
                outputs[0][inputs.input_ids.shape[-1]:], 
                skip_special_tokens=True
            )
            
        except Exception as e:
            raise RuntimeError(f"Error generating text: {str(e)}")

    def test_connection(self) -> bool:
        try:
            test_prompt = "Hello, world!"
            self.generate(test_prompt, max_new_tokens=5)
            return True
        except Exception as e:
            print(f"Connection test failed: {e}")
            return False
