import asyncio
import aiohttp
import json
from typing import Dict, Any, List, Optional
import structlog

from src.config import Config

logger = structlog.get_logger()

class OpenRouterLLMService:
    
    def __init__(self):
        self.api_key = Config.OPENROUTER_API_KEY
        self.base_url = Config.OPENROUTER_BASE_URL
        self.model = Config.OPENROUTER_MODEL
        self.timeout = Config.REQUEST_TIMEOUT
    
    async def generate_response(self, messages: List[Dict[str, str]], **kwargs) -> Optional[str]:
        if not self.api_key:
            logger.error("OpenRouter API key not configured")
            return None
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-Title": "AI Pipeline Project"
        }
        
        payload = {
            "model": self.model,
            "messages": messages,
            **kwargs
        }
        
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                async with session.post(f"{self.base_url}/chat/completions", headers=headers, data=json.dumps(payload)) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result["choices"][0]["message"]["content"]
                    else:
                        logger.error(f"OpenRouter API error: {response.status} - {await response.text()}")
                        return None
        
        except asyncio.TimeoutError:
            logger.error("Timeout while calling OpenRouter API")
            return None
        except Exception as e:
            logger.error(f"Error calling OpenRouter API: {str(e)}")
            return None
    
    async def create_embedding(self, text: str) -> List[float]:
        if not self.api_key:
            logger.error("OpenRouter API key not configured")
            return []
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-Title": "AI Pipeline Project"
        }
        
        payload = {
            "model": "openai/text-embedding-3-small",
            "input": text
        }
        
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                async with session.post(f"{self.base_url}/embeddings", headers=headers, data=json.dumps(payload)) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result["data"][0]["embedding"]
                    elif response.status == 402:
                        logger.error("OpenRouter credits exhausted. Please add credits at https://openrouter.ai/settings/credits")
                        return []
                    else:
                        logger.error(f"OpenRouter embedding API error: {response.status} - {await response.text()}")
                        return []
        
        except asyncio.TimeoutError:
            logger.error("Timeout while creating embedding")
            return []
        except Exception as e:
            logger.error(f"Error creating embedding: {str(e)}")
            return []
    
    async def simple_chat(self, prompt: str, system_prompt: Optional[str] = None) -> Optional[str]:
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": prompt})
        
        return await self.generate_response(messages)
    
    async def analyze_weather_query(self, weather_data: Dict[str, Any]) -> Optional[str]:
        system_prompt = "You are a helpful weather assistant. Provide clear, concise weather information in a friendly tone."
        
        user_prompt = f"""
        Based on the following weather data, provide a natural, human-readable response:
        
        City: {weather_data.get('city', 'Unknown')}
        Temperature: {weather_data.get('temperature', 'N/A')}°C
        Feels like: {weather_data.get('feels_like', 'N/A')}°C
        Description: {weather_data.get('description', 'N/A')}
        Humidity: {weather_data.get('humidity', 'N/A')}%
        Wind Speed: {weather_data.get('wind_speed', 'N/A')} m/s
        
        Make it conversational and informative.
        """
        
        return await self.simple_chat(user_prompt, system_prompt)
    
    async def analyze_document_query(self, query: str, context: str) -> Optional[str]:
        system_prompt = """
        You are a helpful document analysis assistant. Based on the provided document context, 
        answer the user's question accurately and comprehensively. If the context doesn't contain 
        enough information to fully answer the question, acknowledge this limitation and provide 
        the best possible answer with the available information.
        """
        
        user_prompt = f"""
        User Question: {query}
        
        Document Context:
        {context}
        
        Please provide a comprehensive answer based on the document information above.
        """
        
        return await self.simple_chat(user_prompt, system_prompt)
