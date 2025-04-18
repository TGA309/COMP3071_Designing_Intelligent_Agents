import os
from mistralai.client import MistralClient
from mistralai.models.chat_completion import ChatMessage

class MistralBase:
    """Base class for Mistral AI processing pipeline components."""
    
    def __init__(self, api_key=None):
        """
        Initialize Mistral AI connection.
        
        Args:
            api_key (str, optional): Direct API key input.
        """
        self.api_key = self._get_api_key(api_key)
        self.client = self._initialize_client()
        self.model = "mistral-small-latest"  # Using free model as specified
        
    def _get_api_key(self, direct_key=None):
        """Get Mistral API key from .env file."""
        if direct_key:
            return direct_key
        
        # Load environment variables from .env file
        from dotenv import load_dotenv
        load_dotenv()
        
        env_key = os.getenv('MISTRAL_API_KEY')
        if env_key:
            return env_key
        
        raise ValueError("No API key provided. Please set MISTRAL_API_KEY in your .env file.")
    
    def _initialize_client(self):
        """Initialize the Mistral client."""
        return MistralClient(api_key=self.api_key)
    
    def test_connection(self):
        """Test the connection to the Mistral API."""
        try:
            messages = [ChatMessage(role="user", content="Hello, world!")]
            response = self.client.chat(
                model=self.model,
                messages=messages
            )
            return True
        except Exception as e:
            print(f"Connection test failed: {e}")
            return False