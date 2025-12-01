from typing import Dict, Any, List, Optional
import asyncio
import structlog
from langchain_core.messages import HumanMessage, AIMessage

from src.config import Config
from src.services.weather_service import WeatherService
from src.services.pdf_service import PDFService
from src.services.vector_service import get_vector_service
from src.services.llm_service import OpenRouterLLMService

logger = structlog.get_logger()

class PipelineNodes:
    
    def __init__(self):
        self.weather_service = WeatherService()
        self.pdf_service = PDFService()
        self.vector_service = get_vector_service()
        self.llm_service = OpenRouterLLMService()
    
    async def classify_query(self, state: Dict[str, Any]) -> Dict[str, Any]:
        query = state.get("query", "")
        
        weather_keywords = ["weather", "temperature", "rain", "snow", "wind", "humidity", "forecast", "climate"]
        document_keywords = ["document", "pdf", "file", "information", "find", "search", "what", "how", "explain"]
        
        query_lower = query.lower()
        
        if any(keyword in query_lower for keyword in weather_keywords):
            state["query_type"] = "weather"
            state["next_node"] = "weather_fetch"
            logger.info(f"Classified query as weather-related: {query[:50]}...")
        
        elif any(keyword in query_lower for keyword in document_keywords):
            state["query_type"] = "document"
            state["next_node"] = "document_search"
            logger.info(f"Classified query as document-related: {query[:50]}...")
        
        else:
            state["query_type"] = "document"
            state["next_node"] = "document_search"
            logger.info(f"Default classification to document: {query[:50]}...")
        
        return state
    
    async def fetch_weather(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fetch weather data for the specified city.
        
        Args:
            state: Current state containing the city name
            
        Returns:
            Updated state with weather data
        """
        query = state.get("query", "")
        
        # Extract city name from query
        city = self._extract_city_from_query(query)
        
        if not city:
            state["error"] = "Could not determine city from query"
            state["next_node"] = "response_generation"
            return state
        
        # Fetch weather data
        weather_data = await self.weather_service.get_current_weather(city)
        
        if weather_data:
            state["weather_data"] = weather_data
            state["next_node"] = "response_generation"
            logger.info(f"Successfully fetched weather for {city}")
        else:
            state["error"] = f"Could not fetch weather data for {city}"
            state["next_node"] = "response_generation"
            logger.error(f"Failed to fetch weather for {city}")
        
        return state
    
    async def search_documents(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Search documents based on the user query.
        
        Args:
            state: Current state containing the search query
            
        Returns:
            Updated state with search results
        """
        query = state.get("query", "")
        
        logger.info(f"Searching documents for query: {query}")
        
        # Search for similar documents
        search_results = await self.vector_service.search_similar_documents(query)
        
        logger.info(f"Search completed. Found {len(search_results)} results")
        
        if search_results:
            state["search_results"] = search_results
            state["next_node"] = "response_generation"
            logger.info(f"Found {len(search_results)} relevant documents")
            # Log first result for debugging
            if search_results:
                logger.info(f"First result preview: {search_results[0].get('content', '')[:100]}...")
        else:
            state["error"] = "No relevant information found in documents"
            state["next_node"] = "response_generation"
            logger.warning("No documents found for query")
        
        return state
    
    async def generate_response(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a response based on the fetched data.
        
        Args:
            state: Current state with weather data or search results
            
        Returns:
            Updated state with generated response
        """
        query = state.get("query", "")
        query_type = state.get("query_type", "")
        
        if query_type == "weather" and "weather_data" in state:
            # Generate weather response using OpenRouter
            weather_data = state["weather_data"]
            weather_dict = {
                "city": weather_data.city,
                "temperature": weather_data.temperature,
                "feels_like": weather_data.feels_like,
                "description": weather_data.description,
                "humidity": weather_data.humidity,
                "wind_speed": weather_data.wind_speed
            }
            response = await self.llm_service.analyze_weather_query(weather_dict)
            if not response:
                # Fallback to formatted response
                response = self.weather_service.format_weather_response(weather_data)
        
        elif query_type == "document" and "search_results" in state:
            # Generate document response using OpenRouter
            search_results = state["search_results"]
            context = self.vector_service.format_search_results(search_results)
            
            logger.info(f"Document query: {query}")
            logger.info(f"Context being sent to LLM: {context[:500]}...")
            
            try:
                response = await self.llm_service.analyze_document_query(query, context)
                logger.info(f"LLM response: {response[:200]}...")
                
                if not response:
                    # Fallback to raw context
                    response = "I apologize, but I encountered an error while generating a response. Here's the raw information I found:\n\n" + context
            except Exception as e:
                logger.error(f"Error generating LLM response: {str(e)}")
                response = "I apologize, but I encountered an error while generating a response. Here's the raw information I found:\n\n" + context
        
        elif "error" in state:
            response = state["error"]
        
        else:
            response = "I apologize, but I couldn't process your request. Please try again."
        
        state["response"] = response
        state["next_node"] = "__end__"
        
        return state
    
    def _extract_city_from_query(self, query: str) -> Optional[str]:
        """
        Extract city name from weather query.
        
        Args:
            query: User query string
            
        Returns:
            City name or None if not found
        """
        import re
        
        # Common weather query patterns
        patterns = [
            r"weather\s+(?:in|at|for)\s+([A-Za-z\s]+?)(?:\?|$|\s)",
            r"temperature\s+(?:in|at|for)\s+([A-Za-z\s]+?)(?:\?|$|\s)",
            r"(?:what(?:'s| is)\s+the\s+weather\s+(?:in|at|for))\s+([A-Za-z\s]+?)(?:\?|$|\s)",
            r"(?:tell\s+me\s+(?:the\s+)?temperature\s+(?:in|at|for))\s+([A-Za-z\s]+?)(?:\?|$|\s)",
            r"(?:how(?:'s| is)\s+the\s+weather\s+(?:in|at|for))\s+([A-Za-z\s]+?)(?:\?|$|\s)",
            r"(?:what(?:'s| is)\s+the\s+climate\s+(?:today\s+)?(?:in|at|for))\s+([A-Za-z\s]+?)(?:\?|$|\s)",
            r"(?:how(?:'s| is)\s+the\s+climate\s+(?:today\s+)?(?:in|at|for))\s+([A-Za-z\s]+?)(?:\?|$|\s)",
            r"climate\s+(?:today\s+)?(?:in|at|for)\s+([A-Za-z\s]+?)(?:\?|$|\s)",
            r"weather\s+(?:today\s+)?(?:in|at|for)\s+([A-Za-z\s]+?)(?:\?|$|\s)",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                city = match.group(1).strip()
                # Clean up the city name (remove extra words, punctuation)
                city = re.sub(r'\b(the|in|at|for|weather|temperature|climate|today)\b', '', city, flags=re.IGNORECASE)
                city = city.strip('.,!? ').title()
                if city and len(city) > 1:
                    return city
        
        # Fallback: Look for capitalized words that might be city names
        words = query.split()
        for word in words:
            if word[0].isupper() and word.lower() not in ["the", "what", "how", "when", "where", "why", "weather", "temperature", "climate", "tell", "me", "is", "it", "in", "at", "for", "today"]:
                # Check if it's likely a city name (2+ letters, not a question word)
                clean_word = word.strip(".,!?")
                if len(clean_word) >= 2 and clean_word.isalpha():
                    return clean_word
        
        return None
    
    async def load_pdf_documents(self, pdf_path: str) -> bool:
        """
        Load and process PDF documents into the vector database.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            True if successful, False otherwise
        """
        # Extract text chunks from PDF
        chunks = self.pdf_service.extract_text_from_pdf(pdf_path)
        
        if not chunks:
            logger.error(f"Failed to process PDF: {pdf_path}")
            return False
        
        # Store chunks in vector database
        success = await self.vector_service.store_pdf_chunks(chunks)
        
        if success:
            logger.info(f"Successfully loaded PDF: {pdf_path}")
        
        return success
