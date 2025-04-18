import os
os.environ['CUDA_LAUNCH_BLOCKING'] = '1' 
import torch
import time
from llm_pipeline import QueryExpansion

def main():
    # Check if CUDA is available
    print(f"CUDA available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"CUDA device: {torch.cuda.get_device_name(0)}")
        print(f"Total VRAM: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.2f} GB")
    
    # Initialize the query expansion with 8-bit quantization
    print("\nInitializing QueryExpansion with Gemma 3 4B...")
    start_time = time.time()
    query_expander = QueryExpansion(load_in_8bit=False)
    load_time = time.time() - start_time
    print(f"Model loaded in {load_time:.2f} seconds")
    
    # Test connection
    print("\nTesting model connection...")
    if query_expander.llm.test_connection():
        print("✓ Model loaded successfully!")
    else:
        print("× Model connection failed.")
        return
    
    # Test query
    query = "What are for loops in Java?"
    print(f"\nExpanding query: {query}")
    
    result = query_expander.expand_query(query, temperature=0.3, max_new_tokens=1024)
    
    # Display results    
    print("\nExpanded Query (Keywords):")
    # print(result["expanded_query_keywords"])
    print(result)

if __name__ == "__main__":
    main()