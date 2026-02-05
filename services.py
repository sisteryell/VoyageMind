"""
Service singletons for OpenAI and Langfuse.
"""
import os
from threading import Lock
from typing import Optional, Dict, Any
from dotenv import load_dotenv
from openai import AsyncOpenAI
from langfuse import Langfuse

# Load environment variables
load_dotenv()


class Config:
    """Configuration singleton."""
    _instance = None
    _lock = Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._init()
        return cls._instance
    
    def _init(self):
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        self.openai_model = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
        self.langfuse_public_key = os.getenv('LANGFUSE_PUBLIC_KEY')
        self.langfuse_secret_key = os.getenv('LANGFUSE_SECRET_KEY')
        self.langfuse_host = os.getenv('LANGFUSE_HOST', 'https://cloud.langfuse.com')
        
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY required")
        if not self.langfuse_public_key or not self.langfuse_secret_key:
            raise ValueError("LANGFUSE keys required")


class OpenAIClient:
    """OpenAI singleton."""
    _instance = None
    _lock = Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._init()
        return cls._instance
    
    def _init(self):
        config = Config()
        self.client = AsyncOpenAI(api_key=config.openai_api_key)
        self.model = config.openai_model
    
    async def chat_completion(self, messages: list[Dict[str, str]], 
                             temperature: float = 0.7,
                             response_format: Optional[Dict[str, Any]] = None) -> str:
        kwargs = {"model": self.model, "messages": messages, "temperature": temperature}
        if response_format:
            kwargs["response_format"] = response_format
        response = await self.client.chat.completions.create(**kwargs)
        return response.choices[0].message.content
    
    @classmethod
    def get_instance(cls):
        return cls()


class LangfuseClient:
    """Langfuse singleton."""
    _instance = None
    _lock = Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._init()
        return cls._instance
    
    def _init(self):
        config = Config()
        self.client = Langfuse(
            public_key=config.langfuse_public_key,
            secret_key=config.langfuse_secret_key,
            host=config.langfuse_host
        )
    
    def create_trace(self, name: str, metadata: Optional[Dict[str, Any]] = None):
        return self.client.trace(name=name, metadata=metadata)
    
    def flush(self):
        self.client.flush()
    
    @classmethod
    def get_instance(cls):
        return cls()
