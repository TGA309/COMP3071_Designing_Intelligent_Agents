import datetime
import json
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

def call_mistral_api(prompt: str):
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

    return response

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
    
    response = call_mistral_api(prompt)
    
    # Extract and return the expanded keywords
    expanded_keywords = response.choices[0].message.content.strip()
    return expanded_keywords.split(',')

def generate_llm_response(user_prompt, crawled_content):
    """
    Generates an answer to the user's prompt based strictly on the provided crawled content.
    
    Args:
        user_prompt (str): The original user query
        crawled_content (list): List of dictionaries containing scraped content and metadata
        max_sources (int): Maximum number of sources to include
        
    Returns:
        str: The generated answer from Mistral AI
    """
    
    prompt = f"""
    Generate a comprehensive and accurate answer to the following query using ONLY the information provided in the sources below:

    QUERY: {user_prompt}

    SOURCES:
    """
    
    # Add selected crawled content to the prompt
    for i, item in enumerate(crawled_content, 1):
        # Format source header with metadata
        source_header = f"SOURCE [{i}]"
        if 'source' in item and item['source']:
            source_header += f" (Source: {item['source']})" 
        if 'domain' in item and item['domain']:
            source_header += f" from Domain: {item['domain']}"
        if 'title' in item and item['title']:
            source_header += f" - \"{item['title']}\""
            
        # Add the content with clear separation
        prompt += f"\n\n{source_header}\n{'_'*80}\n{item.get('content', 'No content available')}\n{'_'*80}"
    
    prompt += """

    Guidelines for Answer Generation:

    1. **Source Restriction:** Your answer must be based EXCLUSIVELY on the information provided in the sources above. Do not incorporate external knowledge, personal opinions, or information not found in these sources.

    2. **Citation Method:** When using information from a specific source, include a citation in the format [SOURCE X] where X is the source number. Multiple citations can be used if information comes from multiple sources.

    3. **Comprehensive Coverage:** Provide a thorough and detailed answer that addresses all aspects of the query using relevant information from all appropriate sources.

    4. **Information Gaps:** If the sources do not contain sufficient information to fully answer the query, explicitly acknowledge these limitations in your answer.

    5. **Structured Presentation:**
       * Begin with a concise summary of the answer if appropriate
       * Organize information logically with clear sections
       * Use bullet points or numbered lists for clarity when presenting multiple items
       * Present information in order of relevance to the query

    6. **Markdown Formatting:**
       * Use proper Markdown syntax for formatting (headings, code blocks, lists, etc.)
       * For headings, please always use ## for highest level heading and keep adding # as you need to for the subheadings
       * Use actual line breaks instead of escape sequences
       * Format code examples with `````` syntax for proper code highlighting
       * Use **bold** and *italic* formatting appropriately for emphasis

    7. **Direct Response:** Start your answer immediately without restating the query or referring to these instructions.
    
    After completing your answer, add a section titled '## Sources' followed by a numbered list of all sources used, with titles linked to their domains using proper Markdown link syntax:
    
    ## Sources
    1. [Domain1](domain_url_1) - [Title_1](source_url_1)
    2. [Domain2](domain_url_2) - [Title_2](source_url_2)
    etc.

    IMPORTANT: 
    Ensure your response is in pure Markdown format without escape sequences. When creating the Sources section:

    1. Only include sources that you actually referenced in your answer
    2. Format each source entry as follows:
    - [Domain name](domain_url) - [Title](source_url)
    - The domain_url should be the value that appears after "from Domain:" in the source header
    - The source_url should be the value that appears after "Source:" in the source header
    3. If information is missing:
    - If the title is missing, use [No Title](source_url)
    - If domain_url is missing, use the domain name without brackets or links
    - If source_url is missing, mention the title without making it a link
    4. Use the exact URLs as provided in the original sources without modifications
    5. Only include sources that you actually referenced in your answer

    """
    
    response = call_mistral_api(prompt)
    
    # Extract and return the generated answer
    generated_answer = response.choices[0].message.content.strip()
    return generated_answer

def evaluate_responses(user_prompt, raw_results, llm_response):
    """
    Evaluates both raw crawled results and the generated LLM response against the original user prompt.
    
    Args:
        user_prompt (str): The original user query
        raw_results (list): List of dictionaries containing crawled content and metadata
        llm_response (str): The generated answer from the LLM
        
    Returns:
        dict: Evaluation scores and feedback for both raw results and LLM response
    """
    # Evaluate raw results
    raw_results_evaluation = evaluate_raw_results(user_prompt, raw_results)
    
    # Evaluate LLM response
    llm_response_evaluation = evaluate_llm_response(user_prompt, raw_results, llm_response)
    
    # Combine evaluations
    evaluation_results = {
        "raw_results_evaluation": raw_results_evaluation,
        "llm_response_evaluation": llm_response_evaluation,
        "timestamp": datetime.datetime.now().isoformat()
    }
    
    return evaluation_results

def evaluate_raw_results(user_prompt, raw_results):
    """
    Evaluates the raw crawled results for relevance and quality.
    
    Args:
        user_prompt (str): The original user query
        raw_results (list): List of dictionaries containing crawled content and metadata
        
    Returns:
        dict: Evaluation scores and feedback for raw results
    """
    # Extract content from top results (limit to prevent token overload)
    top_results = sorted(raw_results, key=lambda x: x.get('weighted_score', 0), reverse=True)[:3]
    
    # Create content snippets for evaluation
    content_snippets = []
    for i, item in enumerate(top_results, 1):
        snippet = f"Snippet {i}: {item.get('content', '')[:300]}..." # Limit content length
        content_snippets.append(snippet)
    
    content_to_evaluate = "\n\n".join(content_snippets)
    
    prompt = f"""
    You are an expert evaluator assessing search result quality. Analyze these search result snippets for their relevance and usefulness in answering this user query:
    
    QUERY: {user_prompt}
    
    SEARCH RESULT SNIPPETS:
    {content_to_evaluate}
    
    Evaluate these results across the following dimensions, with a score between 0.0 and 1.0 (higher is better) and brief justification for each:
    
    1. Relevance: How directly relevant are these results to the query? Score between 0.0-1.0
    2. Information Completeness: Do the results collectively provide comprehensive information to answer the query? Score between 0.0-1.0
    3. Information Quality: How accurate, authoritative, and trustworthy does the information appear to be? Score between 0.0-1.0
    4. Diversity: Do the results offer different perspectives or complementary information? Score between 0.0-1.0
    
    After analyzing each dimension separately, provide an overall quality score between 0.0-1.0.
    
    FORMAT YOUR RESPONSE AS A VALID JSON OBJECT with this exact structure:
    {{
        "relevance": {{
            "score": 0.0,
            "justification": "explanation"
        }},
        "information_completeness": {{
            "score": 0.0,
            "justification": "explanation"
        }},
        "information_quality": {{
            "score": 0.0,
            "justification": "explanation"
        }},
        "diversity": {{
            "score": 0.0,
            "justification": "explanation"
        }},
        "overall": {{
            "score": 0.0,
            "justification": "explanation"
        }}
    }}
    
    Ensure your response is ONLY the JSON object with no additional text.
    """
    
    response = call_mistral_api(prompt)
    
    try:
        # Extract and parse JSON response
        evaluation_json_str = response.choices[0].message.content.strip()
        # Clean any markdown formatting
        if evaluation_json_str.startswith("```"):
            # Remove the opening code block marker and any language specification
            first_newline = evaluation_json_str.find("\n")
            if first_newline != -1:
                evaluation_json_str = evaluation_json_str[first_newline+1:].strip()
            
        if evaluation_json_str.endswith("```"):
            # Remove the closing code block marker
            evaluation_json_str = evaluation_json_str.rsplit("```", 1)[0].strip()

            
        evaluation_results = json.loads(evaluation_json_str.strip())
        return evaluation_results
    except json.JSONDecodeError:
        # Fallback if JSON parsing fails
        return {
            "error": "Failed to parse evaluation results",
            "raw_response": response.choices[0].message.content
        }

def evaluate_llm_response(user_prompt, raw_results, llm_response):
    """
    Evaluates the LLM-generated response for quality, accuracy and relevance.
    
    Args:
        user_prompt (str): The original user query
        raw_results (list): List of dictionaries containing crawled content and metadata (to check for hallucination)
        llm_response (str): The generated answer from the LLM
        
    Returns:
        dict: Evaluation scores and feedback for LLM response
    """
    # Extract a consolidated version of the source content (limited for token constraints)
    source_content = ""
    for i, item in enumerate(raw_results[:3], 1):  # Limit to top 3 sources
        source_content += f"SOURCE {i}: {item.get('content', '')[:500]}...\n\n"  # Truncate long contents
    
    prompt = f"""
    You are an expert LLM output evaluator. Analyze this generated response against the user query and source information:
    
    QUERY: {user_prompt}
    
    LLM RESPONSE:
    {llm_response}
    
    SOURCE INFORMATION (samples):
    {source_content}
    
    Evaluate the LLM response across these dimensions, scoring each between 0.0 and 1.0 (higher is better) with a brief justification:
    
    1. Correctness: Is the information factually correct based on the sources? Score between 0.0-1.0
    2. Relevance: How directly does it address the user's query? Score between 0.0-1.0
    3. Comprehensiveness: Does it thoroughly cover the topic from the query? Score between 0.0-1.0
    4. Hallucination: Does it contain information not supported by the sources? Score between 0.0-1.0 (1.0 means NO hallucination, 0.0 means severe hallucination)
    5. Clarity: Is the response well-structured, clear, and easy to understand? Score between 0.0-1.0
    
    After analyzing each dimension separately, provide an overall quality score between 0.0-1.0.
    
    FORMAT YOUR RESPONSE AS A VALID JSON OBJECT with this exact structure:
    {{
        "correctness": {{
            "score": 0.0,
            "justification": "explanation"
        }},
        "relevance": {{
            "score": 0.0,
            "justification": "explanation"
        }},
        "comprehensiveness": {{
            "score": 0.0,
            "justification": "explanation"
        }},
        "hallucination": {{
            "score": 0.0,
            "justification": "explanation"
        }},
        "clarity": {{
            "score": 0.0,
            "justification": "explanation"
        }},
        "overall": {{
            "score": 0.0,
            "justification": "explanation"
        }}
    }}
    
    Ensure your response is ONLY the JSON object with no additional text.
    """
    
    response = call_mistral_api(prompt)
    
    try:
        # Extract and parse JSON response
        evaluation_json_str = response.choices[0].message.content.strip()
        # Clean any markdown formatting
        if evaluation_json_str.startswith("```"):
            # Remove the opening code block marker and any language specification
            first_newline = evaluation_json_str.find("\n")
            if first_newline != -1:
                evaluation_json_str = evaluation_json_str[first_newline+1:].strip()
            
        if evaluation_json_str.endswith("```"):
            # Remove the closing code block marker
            evaluation_json_str = evaluation_json_str.rsplit("```", 1)[0].strip()

            
        evaluation_results = json.loads(evaluation_json_str.strip())
        return evaluation_results
    except json.JSONDecodeError:
        # Fallback if JSON parsing fails
        return {
            "error": "Failed to parse evaluation results",
            "raw_response": response.choices[0].message.content
        }