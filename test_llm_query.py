from llm_pipeline import QueryExpansion

# Initialize with API key from config file
query_expander = QueryExpansion()
# Or with direct API key
# query_expander = QueryExpansion(api_key="your_api_key_here")

# Test connection
if query_expander.test_connection():
    print("Connected to Mistral AI successfully!")
else:
    print("Connection failed. Check your API key.")
    exit(1)

# Example query
query = "What are for loops in Java?"
result = query_expander.expand_query(query)

# Display results
print("\nKey Concepts:")
for concept in result["key_concepts"]:
    print(f"- {concept}")

print("\nRelated Terms:")
for concept, terms in result["related_terms"].items():
    print(f"- {concept} → {', '.join(terms)}")

print("\nExpanded Query (Natural Language):")
print(result["expanded_query_nl"])

print("\nExpanded Query (Keywords):")
print(result["expanded_query_keywords"])