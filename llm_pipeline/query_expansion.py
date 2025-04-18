from .base import MistralBase
from mistralai.models.chat_completion import ChatMessage

class QueryExpansion(MistralBase):
    """Class for expanding queries using Mistral AI."""
    
    def __init__(self, api_key=None):
        """Initialize the QueryExpansion component."""
        super().__init__(api_key)
    
    def expand_query(self, query):
        """
        Expand a user query using Mistral AI.
        
        Args:
            query (str): The original user query.
            
        Returns:
            dict: Dictionary containing structured expansion results.
        """
        prompt = self._create_expansion_prompt(query)
        messages = [ChatMessage(role="user", content=prompt)]
        
        response = self.client.chat(
            model=self.model,
            messages=messages
        )
        
        return self._parse_expansion_response(response.choices[0].message.content)
    
    def _create_expansion_prompt(self, query):
        """Create the prompt for query expansion."""
        prompt = f"""
        You are an expert in query expansion for search engines. Your task is to expand the following query to improve search results:

        Original Query: {query}

        Follow these steps and include all sections in your response:

        Step 1: Identify key concepts
        Extract 2-4 main concepts or entities from the query.

        Step 2: List synonyms and related terms for expansion
        For each key concept, provide 3-5 closely related terms, synonyms, or alternative phrasings.

        Step 3: Create an expanded query in natural language
        Formulate a more detailed question that incorporates the related terms and provides more context.

        Step 4: Create an expanded query in keyword-style format
        Create a list of search keywords and phrases separated by commas.

        Your response should be structured exactly as follows:
        Key Concepts:
        - concept1
        - concept2
        ...

        Related Terms:
        - concept1 → term1, term2, term3
        - concept2 → term1, term2, term3
        ...

        Expanded Query (Natural Language):
        [The expanded natural language query]

        Expanded Query (Keywords):
        [The expanded keyword-style query]
        """
        return prompt
    
    def _parse_expansion_response(self, response_text):
        """Parse the response into a structured format."""
        result = {
            "key_concepts": [],
            "related_terms": {},
            "expanded_query_nl": "",
            "expanded_query_keywords": ""
        }
        
        sections = response_text.split("\n\n")
        current_section = None
        
        for section in sections:
            section = section.strip()
            
            if "Key Concepts:" in section:
                current_section = "key_concepts"
                lines = section.split("\n")[1:]  # Skip the header line
                for line in lines:
                    if line.strip().startswith("- "):
                        concept = line.strip()[2:].strip()
                        result["key_concepts"].append(concept)
            
            elif "Related Terms:" in section:
                current_section = "related_terms"
                lines = section.split("\n")[1:]  # Skip the header line
                for line in lines:
                    if line.strip().startswith("- "):
                        parts = line.strip()[2:].split("→")
                        if len(parts) == 2:
                            concept = parts[0].strip()
                            terms = [t.strip() for t in parts[1].split(",")]
                            result["related_terms"][concept] = terms
            
            elif "Expanded Query (Natural Language):" in section:
                current_section = "expanded_query_nl"
                lines = section.split("\n")[1:]  # Skip the header line
                result["expanded_query_nl"] = "\n".join(lines).strip()
            
            elif "Expanded Query (Keywords):" in section:
                current_section = "expanded_query_keywords"
                lines = section.split("\n")[1:]  # Skip the header line
                result["expanded_query_keywords"] = "\n".join(lines).strip()
        
        return result