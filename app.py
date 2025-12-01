import streamlit as st
import asyncio
import sys
import os
from datetime import datetime
from typing import Dict, Any, List
import structlog

sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.config import Config
from src.graph.pipeline import AIPipeline
from src.evaluation.langsmith_evaluator import LangSmithEvaluator

# Configure Streamlit page
st.set_page_config(
    page_title="AI Pipeline Demo",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .chat-message {
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
        display: flex;
        flex-direction: column;
    }
    .user-message {
        background-color: #e3f2fd;
        border-left: 4px solid #2196f3;
    }
    .assistant-message {
        background-color: #f3e5f5;
        border-left: 4px solid #9c27b0;
    }
    .weather-message {
        background-color: #e8f5e8;
        border-left: 4px solid #4caf50;
    }
    .document-message {
        background-color: #fff3e0;
        border-left: 4px solid #ff9800;
    }
    .metric-card {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid #dee2e6;
    }
    .stButton > button {
        background-color: #2196f3;
        color: white;
        border: none;
        padding: 0.5rem 1rem;
        border-radius: 0.25rem;
        font-weight: 500;
    }
    .stButton > button:hover {
        background-color: #1976d2;
    }
</style>
""", unsafe_allow_html=True)

class StreamlitApp:
    """Main Streamlit application class."""
    
    def __init__(self):
        self.pipeline = None
        self.evaluator = None
        self.conversation_chain = None
        self.initialize_services()
    
    def initialize_services(self):
        """Initialize pipeline and evaluation services."""
        try:
            # Validate configuration
            if not Config.validate():
                st.error("⚠️ Please configure your environment variables. Check the .env file.")
                return
            
            # Initialize pipeline
            self.pipeline = AIPipeline()
            
            # Initialize evaluator
            self.evaluator = LangSmithEvaluator()
            
            # Create conversation chain
            self.conversation_chain = self.pipeline.create_conversation_chain()
            
            st.success("✅ AI Pipeline initialized successfully!")
            
        except Exception as e:
            import traceback
            st.error(f"❌ Error initializing services: {str(e)}")
            st.error(f"Details: {traceback.format_exc()}")
            st.stop()
    
    def render_sidebar(self):
        """Render the sidebar with controls and information."""
        st.sidebar.title("🤖 AI Pipeline Controls")
        
        # Configuration status
        st.sidebar.subheader("📊 Configuration Status")
        
        config_status = {
            "OpenRouter API": "✅" if Config.OPENROUTER_API_KEY else "❌",
            "Weather API": "✅" if Config.OPENWEATHERMAP_API_KEY else "❌",
            "LangSmith": "✅" if Config.LANGSMITH_TRACING else "⚪"
        }
        
        for service, status in config_status.items():
            st.sidebar.write(f"{service}: {status}")
        
        st.sidebar.divider()
        
        # PDF Upload
        st.sidebar.subheader("📄 Document Management")
        
        uploaded_file = st.sidebar.file_uploader(
            "Upload PDF Document",
            type=['pdf'],
            help="Upload a PDF document to add to the knowledge base"
        )
        
        if uploaded_file is not None:
            if st.sidebar.button("📥 Load PDF", key="load_pdf"):
                self.load_pdf_document(uploaded_file)
        
        st.sidebar.divider()
        
        # Pipeline Status
        st.sidebar.subheader("🔍 Pipeline Status")
        
        if st.sidebar.button("🔄 Refresh Status", key="refresh_status"):
            self.refresh_pipeline_status()
        
        # Display status if available
        if "pipeline_status" in st.session_state:
            status = st.session_state.pipeline_status
            st.sidebar.json(status)
        
        st.sidebar.divider()
        
        # Evaluation
        st.sidebar.subheader("📈 Evaluation")
        
        if Config.LANGSMITH_TRACING:
            st.sidebar.write("LangSmith tracing is enabled")
            if st.sidebar.button("📊 View Evaluation Report", key="view_eval"):
                self.show_evaluation_report()
        else:
            st.sidebar.write("LangSmith tracing is disabled")
    
    def load_pdf_document(self, uploaded_file):
        """Load uploaded PDF document into the pipeline."""
        try:
            # Save uploaded file temporarily
            temp_path = f"temp_{uploaded_file.name}"
            with open(temp_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            # Load into pipeline
            with st.spinner("Processing PDF document..."):
                success = asyncio.run(self.pipeline.load_pdf(temp_path))
            
            # Clean up temp file
            os.remove(temp_path)
            
            if success:
                st.success(f"✅ Successfully loaded: {uploaded_file.name}")
                st.session_state.pdf_loaded = True
                # Refresh pipeline status
                self.refresh_pipeline_status()
            else:
                st.error(f"❌ Failed to load: {uploaded_file.name}")
        
        except Exception as e:
            st.error(f"❌ Error loading PDF: {str(e)}")
    
    def refresh_pipeline_status(self):
        """Refresh and display pipeline status."""
        try:
            with st.spinner("Fetching pipeline status..."):
                status = asyncio.run(self.pipeline.get_pipeline_status())
            st.session_state.pipeline_status = status
        except Exception as e:
            st.error(f"Error fetching status: {str(e)}")
    
    def show_evaluation_report(self):
        """Show evaluation report in a modal."""
        try:
            # This would typically fetch real evaluation data
            st.info("📊 Evaluation report feature coming soon!")
        except Exception as e:
            st.error(f"Error showing evaluation: {str(e)}")
    
    def render_chat_interface(self):
        """Render the main chat interface."""
        st.title("🤖 AI Pipeline Chat Interface")
        st.markdown("Ask me about the weather or questions about your uploaded documents!")
        
        # Initialize chat history
        if "messages" not in st.session_state:
            st.session_state.messages = []
        
        # Display chat messages
        for message in st.session_state.messages:
            self.display_message(message)
        
        # Chat input
        if prompt := st.chat_input("Ask me anything..."):
            asyncio.run(self.handle_user_input(prompt))
    
    def display_message(self, message: Dict[str, Any]):
        """Display a chat message with appropriate styling."""
        with st.container():
            if message["role"] == "user":
                st.markdown(f"""
                <div class="chat-message user-message">
                    <strong>👤 You:</strong><br>
                    {message["content"]}
                </div>
                """, unsafe_allow_html=True)
            else:
                # Determine message type for styling
                query_type = message.get("query_type", "document")
                css_class = "weather-message" if query_type == "weather" else "document-message"
                
                icon = "🌤️" if query_type == "weather" else "📄"
                
                st.markdown(f"""
                <div class="chat-message assistant-message {css_class}">
                    <strong>{icon} AI Assistant:</strong><br>
                    {message["content"]}
                </div>
                """, unsafe_allow_html=True)
                
                # Show metadata if available
                if "metadata" in message:
                    with st.expander("📊 Query Details"):
                        st.json(message["metadata"])
    
    async def handle_user_input(self, prompt: str):
        """Handle user input and generate response."""
        # Add user message to chat
        user_message = {
            "role": "user",
            "content": prompt,
            "timestamp": datetime.now().isoformat()
        }
        st.session_state.messages.append(user_message)
        
        # Display user message immediately
        self.display_message(user_message)
        
        # Generate AI response
        with st.spinner("🤔 Thinking..."):
            try:
                # Process query through pipeline
                result = await self.pipeline.process_query(prompt)
                
                if result["success"]:
                    response_content = result["response"]
                    query_type = result["query_type"]
                    
                    # Log to LangSmith if enabled
                    if Config.LANGSMITH_TRACING and self.evaluator:
                        await self.evaluator.log_pipeline_run(
                            query=prompt,
                            response=response_content,
                            query_type=query_type,
                            metadata={"source": "streamlit_app"}
                        )
                    
                    # Create assistant message
                    assistant_message = {
                        "role": "assistant",
                        "content": response_content,
                        "query_type": query_type,
                        "timestamp": datetime.now().isoformat(),
                        "metadata": {
                            "processing_time": result.get("processing_time", 0),
                            "query_type": query_type,
                            "success": True
                        }
                    }
                else:
                    # Handle error case
                    assistant_message = {
                        "role": "assistant",
                        "content": f"❌ Sorry, I encountered an error: {result.get('error', 'Unknown error')}",
                        "query_type": "error",
                        "timestamp": datetime.now().isoformat(),
                        "metadata": {
                            "error": result.get("error"),
                            "success": False
                        }
                    }
                
                # Add to chat history
                st.session_state.messages.append(assistant_message)
                
                # Display assistant message
                self.display_message(assistant_message)
                
            except Exception as e:
                error_message = {
                    "role": "assistant",
                    "content": f"❌ An unexpected error occurred: {str(e)}",
                    "query_type": "error",
                    "timestamp": datetime.now().isoformat(),
                    "metadata": {"error": str(e), "success": False}
                }
                st.session_state.messages.append(error_message)
                self.display_message(error_message)
    
    def render_metrics_dashboard(self):
        """Render a metrics dashboard."""
        st.subheader("📊 Pipeline Metrics")
        
        # Create columns for metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                label="Total Queries",
                value=len([m for m in st.session_state.messages if m["role"] == "user"]),
                delta="New session"
            )
        
        with col2:
            weather_queries = len([
                m for m in st.session_state.messages 
                if m["role"] == "assistant" and m.get("query_type") == "weather"
            ])
            st.metric(
                label="Weather Queries",
                value=weather_queries
            )
        
        with col3:
            doc_queries = len([
                m for m in st.session_state.messages 
                if m["role"] == "assistant" and m.get("query_type") == "document"
            ])
            st.metric(
                label="Document Queries",
                value=doc_queries
            )
        
        with col4:
            errors = len([
                m for m in st.session_state.messages 
                if m["role"] == "assistant" and m.get("query_type") == "error"
            ])
            st.metric(
                label="Errors",
                value=errors,
                delta="0" if errors == 0 else "⚠️"
            )
    
    def render_examples_section(self):
        """Render example queries section."""
        st.subheader("💡 Example Queries")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Weather Queries:**")
            weather_examples = [
                "What's the weather in London?",
                "Tell me the temperature in New York",
                "How's the weather in Tokyo today?"
            ]
            for example in weather_examples:
                if st.button(example, key=f"weather_{example}"):
                    asyncio.run(self.handle_user_input(example))
        
        with col2:
            st.markdown("**Document Queries:**")
            doc_examples = [
                "What information do you have about AI?",
                "Find documents about machine learning",
                "Explain the concept of neural networks"
            ]
            for example in doc_examples:
                if st.button(example, key=f"doc_{example}"):
                    asyncio.run(self.handle_user_input(example))
    
    def run(self):
        """Run the Streamlit application."""
        # Render sidebar
        self.render_sidebar()
        
        # Main content area
        tab1, tab2, tab3 = st.tabs(["💬 Chat", "📊 Metrics", "💡 Examples"])
        
        with tab1:
            self.render_chat_interface()
        
        with tab2:
            self.render_metrics_dashboard()
        
        with tab3:
            self.render_examples_section()
        
        # Footer
        st.markdown("---")
        st.markdown(
            "🤖 **AI Pipeline Demo** | Built with LangChain, LangGraph, and LangSmith | "
            "Powered by OpenRouter and Qdrant"
        )

def main():
    """Main entry point for the Streamlit app."""
    app = StreamlitApp()
    app.run()

if __name__ == "__main__":
    main()
