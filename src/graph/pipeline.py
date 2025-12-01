from typing import Dict, Any, Optional
import asyncio
import structlog
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage

from src.config import Config
from src.graph.nodes import PipelineNodes

logger = structlog.get_logger()

class AIPipeline:
    
    def __init__(self):
        self.nodes = PipelineNodes()
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        
        workflow = StateGraph(dict)
        
        workflow.add_node("classify_query", self.nodes.classify_query)
        workflow.add_node("weather_fetch", self.nodes.fetch_weather)
        workflow.add_node("document_search", self.nodes.search_documents)
        workflow.add_node("response_generation", self.nodes.generate_response)
        
        workflow.set_entry_point("classify_query")
        
        workflow.add_conditional_edges(
            "classify_query",
            lambda state: state.get("next_node", "response_generation"),
            {
                "weather_fetch": "weather_fetch",
                "document_search": "document_search",
                "response_generation": "response_generation"
            }
        )
        
        workflow.add_edge("weather_fetch", "response_generation")
        workflow.add_edge("document_search", "response_generation")
        
        workflow.add_edge("response_generation", END)
        
        return workflow.compile()
    
    async def process_query(self, query: str) -> Dict[str, Any]:
        try:
            initial_state = {
                "query": query,
                "query_type": None,
                "weather_data": None,
                "search_results": None,
                "response": None,
                "error": None,
                "next_node": None
            }
            
            # Process through the graph
            result = await self.graph.ainvoke(initial_state)
            
            # Log the result for LangSmith
            if Config.LANGSMITH_TRACING:
                logger.info(f"Query processed successfully", 
                           query=query, 
                           query_type=result.get("query_type"),
                           response_length=len(result.get("response", "")))
            
            return {
                "success": True,
                "query": query,
                "query_type": result.get("query_type"),
                "response": result.get("response", ""),
                "error": result.get("error")
            }
        
        except Exception as e:
            logger.error(f"Error processing query: {str(e)}")
            return {
                "success": False,
                "query": query,
                "response": "",
                "error": f"An error occurred while processing your request: {str(e)}"
            }
    
    async def load_pdf(self, pdf_path: str) -> bool:
        try:
            success = await self.nodes.load_pdf_documents(pdf_path)
            if success:
                logger.info(f"Successfully loaded PDF: {pdf_path}")
            else:
                logger.error(f"Failed to load PDF: {pdf_path}")
            return success
        except Exception as e:
            logger.error(f"Error loading PDF {pdf_path}: {str(e)}")
            return False
    
    async def get_pipeline_status(self) -> Dict[str, Any]:
        try:
            collection_info = await self.nodes.vector_service.get_collection_info()
            
            return {
                "pipeline_status": "active",
                "vector_database": {
                    "collection_name": Config.QDRANT_COLLECTION_NAME,
                    "documents_count": collection_info.get("points_count", 0),
                    "indexed_count": collection_info.get("indexed_vectors_count", 0),
                    "status": collection_info.get("status", "unknown")
                },
                "services": {
                    "weather_service": "configured" if Config.OPENWEATHERMAP_API_KEY else "not_configured",
                    "openrouter_llm": "configured" if Config.OPENROUTER_API_KEY else "not_configured",
                    "langsmith_tracing": "enabled" if Config.LANGSMITH_TRACING else "disabled"
                }
            }
        except Exception as e:
            logger.error(f"Error getting pipeline status: {str(e)}")
            return {
                "pipeline_status": "error",
                "error": str(e)
            }
    
    def create_conversation_chain(self):
        class ConversationChain:
            def __init__(self, pipeline):
                self.pipeline = pipeline
                self.conversation_history = []
            
            async def chat(self, message: str) -> str:
                """Chat with the AI pipeline."""
                self.conversation_history.append(HumanMessage(content=message))
                
                result = await self.pipeline.process_query(message)
                
                response = result.get("response", "I apologize, but I couldn't process your request.")
                
                self.conversation_history.append(AIMessage(content=response))
                
                return response
            
            def get_history(self) -> list:
                """Get the conversation history."""
                return self.conversation_history
        
        return ConversationChain(self)
