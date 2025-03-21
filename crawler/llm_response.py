# llm_response.py

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from huggingface_hub import snapshot_download, login
# login()
from pathlib import Path
from config import config

def generate_llm_response(crawler_results, user_prompt):
    """
    Generate a response using the phi-4 pretrained LLM strictly based on crawler results.
    
    Args:
        crawler_results (list): List of dictionaries containing content and scores from the crawler.
        user_prompt (str): The user's query or prompt.
        
    Returns:
        str: Generated response from the LLM.
    """
    # Setup model caching
    model_path = config.model.MODEL_CACHE_DIR / config.model.LLM_MODEL_NAME.split('/')[-1]
    
    # Download model if it doesn't exist
    if not model_path.exists():
        print(f"Downloading model {config.model.LLM_MODEL_NAME} for first time use...")
        snapshot_download(repo_id=config.model.LLM_MODEL_NAME, local_dir=str(model_path))
    
    # Load the phi-4 pretrained model and tokenizer from cache
    tokenizer = AutoTokenizer.from_pretrained(str(model_path))
    model = AutoModelForCausalLM.from_pretrained(str(model_path))
    
    # Prepare the input strictly using crawler results
    context = "\n\n".join([f"[Source {i+1}] (Score: {result['score']:.2f})\n{result['content']}" 
                          for i, result in enumerate(crawler_results)])
    
    # Create a prompt that instructs the model to use only the provided information
    input_text = f"""You are a helpful assistant that answers questions based only on the provided information.

User Question: {user_prompt}

Information:
{context}

Answer the question using only the information provided above. If the information doesn't contain the answer, say so."""
    
    # Tokenize the input
    inputs = tokenizer(input_text, return_tensors="pt", truncation=True, max_length=1024)
    
    # Generate the response
    with torch.no_grad():
        outputs = model.generate(
            inputs["input_ids"],
            max_length=1536,  # Allow for longer responses
            num_beams=4,
            temperature=0.7,
            top_p=0.9,
            repetition_penalty=1.2,
            early_stopping=True
        )
    
    # Decode the response and extract just the answer part
    full_response = tokenizer.decode(outputs[0], skip_special_tokens=True)
    
    # Try to extract just the answer part (after our prompt)
    answer_start = full_response.find("Answer the question")
    if answer_start != -1:
        # Find the next line after the instruction
        next_line = full_response.find("\n", answer_start)
        if next_line != -1:
            return full_response[next_line:].strip()
    
    # Fallback to returning the whole response
    return full_response