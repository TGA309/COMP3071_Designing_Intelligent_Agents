import os
from dotenv import load_dotenv
from mistralai import Mistral

# Load environment variables from .env file
load_dotenv()

# Get the API key from environment variables
api_key = os.getenv("MISTRAL_API_KEY")
if not api_key:
    raise ValueError("MISTRAL_API_KEY not found in .env file")

# Initialize Mistral AI client
client = Mistral(api_key=api_key)

def query_expansion(query_text, n_keywords=6):
    """
    Expands a user query into a comma-separated list of search keywords and phrases.
    
    Args:
        query_text (str): The original user query
        
    Returns:
        str: A comma-separated list of expanded keywords and phrases
    """
    prompt = f"""
Generate exactly {n_keywords} diverse and highly relevant search keywords/phrases derived from the following query:

Query: {query_text}

Guidelines for Keyword Generation:
1.  **Relevance & Intent:** Keywords must be directly relevant to the exact core topic and likely user intent behind the query while not deviating from the core topic.
2.  **Diversity:** Include a variety of term types:
    * Core concepts/terms from the query.
    * Synonyms and close semantic variations.
    * Different phrasings or word forms (e.g., "configure setting" vs "setting configuration").
    * Broader or narrower related concepts.
    * Specific technical terms, product names, or jargon if applicable.
3.  **Search Utility:** The keywords should be terms someone might realistically use when searching for information related to the query.
4.  **Quantity:** Provide exactly {n_keywords} unique keywords/phrases.

Output Format:
- Return *only* a comma-separated list of the generated keywords/phrases.
- No introductory text, labels, explanations, or bullet points in the final output.
"""
    
    # Create messages for the API call
    messages = [
        {
            "role": "user",
            "content": prompt
        }
    ]
    
    # Call the Mistral API
    response = client.chat.complete(
        model="mistral-small-latest",  # Using a smaller model for efficiency
        messages=messages
    )
    
    # Extract and return the expanded keywords
    expanded_keywords = response.choices[0].message.content.strip()
    return expanded_keywords.split(',')

# Function 2: To be implemented later

# Function 3: To be implemented later

# Example usage
if __name__ == "__main__":
    test_query = "What are for loops in Java?"
    expanded = query_expansion(test_query)
    print(f"Original query: {test_query}")
    print(f"Expanded keywords: {expanded}")