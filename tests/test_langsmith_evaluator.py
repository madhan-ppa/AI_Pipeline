import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from src.evaluation.langsmith_evaluator import LangSmithEvaluator, EvaluationResult

class TestLangSmithEvaluator:
    
    @pytest.fixture
    def evaluator(self):
        return LangSmithEvaluator()
    
    @pytest.mark.asyncio
    async def test_evaluate_response_weather(self, evaluator):
        with patch.object(evaluator.llm_service, 'simple_chat') as mock_chat:
            mock_chat.return_value = "Score: 0.8\nFeedback: Good weather information provided"
            
            result = await evaluator.evaluate_response(
                query="What's the weather in London?",
                response="Weather in London: 22°C, partly cloudy",
                query_type="weather"
            )
            
            assert isinstance(result, EvaluationResult)
            assert result.score == 0.8
            assert "Good weather information" in result.feedback
    
    @pytest.mark.asyncio
    async def test_evaluate_response_document(self, evaluator):
        with patch.object(evaluator.llm_service, 'simple_chat') as mock_chat:
            mock_chat.return_value = "Score: 0.9\nFeedback: Relevant and accurate answer"
            
            result = await evaluator.evaluate_response(
                query="What is AI?",
                response="AI stands for Artificial Intelligence, a transformative technology",
                query_type="document"
            )
            
            assert isinstance(result, EvaluationResult)
            assert result.score == 0.9
            assert "Relevant and accurate" in result.feedback
    
    @pytest.mark.asyncio
    async def test_log_pipeline_run(self, evaluator):
        with patch.object(evaluator, 'client') as mock_client:
            mock_run = Mock()
            mock_run.id = "test_run_id"
            mock_client.create_run = Mock(return_value=mock_run)
            
            result = await evaluator.log_pipeline_run(
                query="Test query",
                response="Test response",
                query_type="weather"
            )
            
            assert result == "test_run_id"
    
    def test_generate_evaluation_report(self, evaluator):
        results = [
            EvaluationResult(score=0.8, feedback="Good", metrics={}, run_id="1"),
            EvaluationResult(score=0.9, feedback="Excellent", metrics={}, run_id="2"),
            EvaluationResult(score=0.7, feedback="Fair", metrics={}, run_id="3")
        ]
        
        report = evaluator.generate_evaluation_report(results)
        
        assert report["total_evaluations"] == 3
        assert abs(report["average_score"] - 0.8) < 0.001
        assert report["min_score"] == 0.7
        assert report["max_score"] == 0.9
