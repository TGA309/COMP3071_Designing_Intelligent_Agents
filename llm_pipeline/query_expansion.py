from .base import LLMBase, HuggingFaceLLM
from typing import Dict, Any, Optional, Callable
import torch

class QueryExpansion:
    """Class for expanding queries using Gemma 3 4B"""
    
    def __init__(self,
                 llm: Optional[LLMBase] = None,
                 model_name: str = "gghfez/gemma-3-4b-novision",
                 load_in_8bit: bool = True):
        self.llm = llm or HuggingFaceLLM(
            model_name=model_name,
            load_in_8bit=load_in_8bit
        )
    
    def expand_query(self, query: str, **kwargs) -> Dict[str, Any]:
        prompt = self._create_expansion_prompt(query)
        response = self.llm.generate(prompt, **kwargs)
        # return self._parse_expansion_response(response)
        return response
    
    def _create_expansion_prompt(self, query: str) -> str:
        return f"""You are a search query expansion expert. Expand this query:

Original Query: {query}

Give me the expanded query in comma seperated keyword form like this:

Keyword Expansion:
[comma-separated keywords]"""

    def _parse_expansion_response(self, response_text: str) -> Dict[str, Any]:
        result = {
            "key_concepts": [],
            "related_terms": {},
            "expanded_query_nl": "",
            "expanded_query_keywords": ""
        }

        current_section = None
        for line in response_text.split('\n'):
            line = line.strip()
            if not line:
                continue

            elif line.startswith("Keyword Expansion:"):
                current_section = "expanded_query_keywords"
                # *** ADDED CHECK: Try to extract keywords from the same line ***
                parts = line.split(":", 1) # Split only once
                if len(parts) > 1 and parts[1].strip():
                    result["expanded_query_keywords"] = parts[1].strip()
            
            elif current_section == "expanded_query_keywords" and not result["expanded_query_keywords"]:
                result["expanded_query_keywords"] = line # Assign the whole line if it's the next line data

        return result