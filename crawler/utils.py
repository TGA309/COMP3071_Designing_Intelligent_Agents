# crawler/utils.py

import re

def clean_text(text: str) -> str:
    """Clean extracted text content."""
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text)
    # Remove URLs
    text = re.sub(
        r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+',
        '',
        text
    )
    # Remove email addresses
    text = re.sub(r'[\w\.-]+@[\w\.-]+', '', text)
    return text.strip()