import asyncio
import time
import sys
import os
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import structlog
from langsmith import Client

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

try:
    from src.config import Config
    from src.services.llm_service import OpenRouterLLMService
except ImportError as e:
    print(f"Warning: Could not import modules: {e}")
    Config = None
    OpenRouterLLMService = None

logger = structlog.get_logger()

@dataclass
class EvaluationResult:
    score: float
    feedback: str
    metrics: Dict[str, Any]
    run_id: str

class LangSmithEvaluator:
    
    def __init__(self):
        if not Config or not Config.LANGSMITH_API_KEY:
            print("Warning: LangSmith API key not configured - evaluation disabled")
            self.client = None
        else:
            self.client = Client(
                api_key=Config.LANGSMITH_API_KEY,
                api_url="https://api.smith.langchain.com"
            )
        
        if OpenRouterLLMService:
            self.llm_service = OpenRouterLLMService()
        else:
            self.llm_service = None
        
        self.evaluation_prompt_template = """
        Please evaluate the following AI response based on the given criteria:

        User Query: {query}
        AI Response: {response}
        Query Type: {query_type}

        Evaluation Criteria:
        {criteria}

        Please provide:
        1. A score from 0.0 to 1.0
        2. Brief feedback explaining the score

        Format your response as:
        Score: [0.0-1.0]
        Feedback: [Your feedback]
        """
    
    async def log_pipeline_run(self, query: str, response: str, query_type: str, 
                              metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Log a pipeline run to LangSmith.
        
        Args:
            query: User query
            response: AI response
            query_type: Type of query (weather/document)
            metadata: Additional metadata
            
        Returns:
            Run ID if successful, None otherwise
        """
        if not self.client:
            print("Warning: LangSmith client not available - skipping logging")
            return None
        
        try:
            run_data = {
                "input": query,
                "output": response,
                "metadata": {
                    "query_type": query_type,
                    "response_length": len(response),
                    "timestamp": time.time(),
                    **(metadata or {})
                }
            }
            
            # Create a run in LangSmith
            run = self.client.create_run(
                name="ai_pipeline_query",
                inputs={"query": query},
                project_name=Config.LANGSMITH_PROJECT,
                tags=[query_type, "ai_pipeline"],
                run_type="chain"
            )
            
            # Log the output
            if run and run.id:
                self.client.create_run(
                    name="ai_pipeline_response",
                    inputs={"query": query},
                    outputs={"response": response},
                    project_name=Config.LANGSMITH_PROJECT,
                    tags=[query_type, "ai_pipeline_response"],
                    parent_id=run.id,
                    run_type="chain"
                )
                print(f"Logged pipeline run to LangSmith: {run.id}")
                return run.id
            else:
                print("Warning: Failed to create LangSmith run - no run ID")
                return None
        
        except Exception as e:
            print(f"Error logging to LangSmith: {str(e)}")
            return None
    
    async def evaluate_response(self, query: str, response: str, query_type: str, 
                              reference_answer: Optional[str] = None) -> EvaluationResult:
        """
        Evaluate a response using LLM-based evaluation.
        
        Args:
            query: User query
            response: AI response
            query_type: Type of query (weather/document)
            reference_answer: Optional reference answer for comparison
            
        Returns:
            Evaluation result with score and feedback
        """
        try:
            if not self.llm_service:
                print("Warning: LLM service not available - returning default evaluation")
                return EvaluationResult(
                    score=0.5,
                    feedback="LLM service not available for evaluation",
                    metrics={"error": "no_llm_service"},
                    run_id=f"eval_{int(time.time())}"
                )
            
            # Define evaluation criteria based on query type
            if query_type == "weather":
                criteria = """
                - Weather Data Accuracy (40%): Does the response contain accurate weather information?
                - Format (30%): Is the weather information properly formatted and readable?
                - Completeness (30%): Does the response include relevant weather metrics like temperature, humidity, etc.?
                """
            else:
                criteria = """
                - Relevance (40%): Is the response relevant to the user's query?
                - Accuracy (30%): Is the information provided accurate?
                - Completeness (30%): Does the response fully answer the user's question?
                """
            
            # Create evaluation prompt
            evaluation_prompt = self.evaluation_prompt_template.format(
                query=query,
                response=response,
                query_type=query_type,
                criteria=criteria
            )
            
            # Get evaluation from LLM
            evaluation_result = await self.llm_service.simple_chat(evaluation_prompt)
            
            # Parse the evaluation result
            score = 0.0
            feedback = "Evaluation failed to parse"
            
            if evaluation_result:
                lines = evaluation_result.strip().split('\n')
                for line in lines:
                    if line.startswith('Score:'):
                        try:
                            score_str = line.split(':')[1].strip()
                            score = float(score_str)
                        except:
                            score = 0.5  # Default score if parsing fails
                    elif line.startswith('Feedback:'):
                        feedback = line.split(':', 1)[1].strip()
            
            # Additional metrics
            metrics = {
                "response_length": len(response),
                "query_length": len(query),
                "query_type": query_type,
                "evaluation_method": "llm_based"
            }
            
            # Log evaluation to LangSmith if available
            await self._log_evaluation(query, response, score, feedback, metrics)
            
            return EvaluationResult(
                score=score,
                feedback=feedback,
                metrics=metrics,
                run_id=f"eval_{int(time.time())}"
            )
        
        except Exception as e:
            print(f"Error evaluating response: {str(e)}")
            return EvaluationResult(
                score=0.0,
                feedback=f"Evaluation error: {str(e)}",
                metrics={"error": str(e)},
                run_id=""
            )
    
    async def _log_evaluation(self, query: str, response: str, score: float, 
                            feedback: str, metrics: Dict[str, Any]):
        """Log evaluation results to LangSmith."""
        if not self.client:
            return
        
        try:
            self.client.create_run(
                name="ai_pipeline_evaluation",
                inputs={"query": query, "response": response},
                outputs={
                    "score": score,
                    "feedback": feedback,
                    "metrics": metrics
                },
                project_name=Config.LANGSMITH_PROJECT,
                tags=["evaluation", "ai_pipeline"]
            )
        except Exception as e:
            print(f"Error logging evaluation: {str(e)}")
    
    async def run_batch_evaluation(self, test_cases: List[Dict[str, Any]]) -> List[EvaluationResult]:
        """
        Run evaluation on a batch of test cases.
        
        Args:
            test_cases: List of test cases with query, expected_response, and query_type
            
        Returns:
            List of evaluation results
        """
        results = []
        
        for i, test_case in enumerate(test_cases):
            try:
                result = await self.evaluate_response(
                    query=test_case["query"],
                    response=test_case["response"],
                    query_type=test_case["query_type"],
                    reference_answer=test_case.get("reference_answer")
                )
                results.append(result)
                
                # Add delay to avoid rate limiting
                await asyncio.sleep(0.1)
                
            except Exception as e:
                print(f"Error evaluating test case {i}: {str(e)}")
                results.append(EvaluationResult(
                    score=0.0,
                    feedback=f"Evaluation error: {str(e)}",
                    metrics={},
                    run_id=""
                ))
        
        return results
    
    def generate_evaluation_report(self, results: List[EvaluationResult]) -> Dict[str, Any]:
        """Generate a summary report from evaluation results."""
        if not results:
            return {"error": "No evaluation results available"}
        
        scores = [r.score for r in results]
        
        report = {
            "total_evaluations": len(results),
            "average_score": sum(scores) / len(scores),
            "min_score": min(scores),
            "max_score": max(scores),
            "score_distribution": {
                "excellent": len([s for s in scores if s >= 0.9]),
                "good": len([s for s in scores if 0.7 <= s < 0.9]),
                "fair": len([s for s in scores if 0.5 <= s < 0.7]),
                "poor": len([s for s in scores if s < 0.5])
            },
            "common_feedback": self._analyze_feedback(results),
            "performance_metrics": self._analyze_metrics(results)
        }
        
        return report
    
    def _analyze_feedback(self, results: List[EvaluationResult]) -> List[str]:
        """Analyze common feedback themes."""
        feedback_list = [r.feedback for r in results if r.feedback]
        
        # Simple keyword analysis
        common_issues = []
        if any("accuracy" in feedback.lower() for feedback in feedback_list):
            common_issues.append("Accuracy issues detected")
        if any("relevance" in feedback.lower() for feedback in feedback_list):
            common_issues.append("Relevance issues detected")
        if any("completeness" in feedback.lower() for feedback in feedback_list):
            common_issues.append("Completeness issues detected")
        
        return common_issues if common_issues else ["No major issues detected"]
    
    def _analyze_metrics(self, results: List[EvaluationResult]) -> Dict[str, Any]:
        """Analyze performance metrics."""
        response_lengths = [r.metrics.get("response_length", 0) for r in results]
        response_times = [r.metrics.get("response_time", 0) for r in results]
        
        return {
            "average_response_length": sum(response_lengths) / len(response_lengths) if response_lengths else 0,
            "average_response_time": sum(response_times) / len(response_times) if response_times else 0,
            "total_responses": len(results)
        }
