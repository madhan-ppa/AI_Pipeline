#!/usr/bin/env python3
"""
Comprehensive AI Pipeline Evaluation Script

This script runs the complete evaluation pipeline:
1. Runs unit tests
2. Generates LangSmith evaluation reports
3. Captures screenshots
4. Creates comprehensive evaluation report
"""

import asyncio
import sys
import os
from datetime import datetime
from pathlib import Path

sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.utils.test_results_generator import TestResultsGenerator
from src.utils.screenshot_generator import ScreenshotGenerator
from src.evaluation.langsmith_evaluator import LangSmithEvaluator
from src.graph.pipeline import AIPipeline
from src.config import Config

async def main():
    """Run comprehensive pipeline evaluation."""
    print("Starting AI Pipeline Comprehensive Evaluation")
    print("=" * 60)
    
    # Initialize components
    test_generator = TestResultsGenerator()
    screenshot_generator = ScreenshotGenerator()
    evaluator = LangSmithEvaluator()
    pipeline = AIPipeline()
    
    evaluation_results = {
        "timestamp": datetime.now().isoformat(),
        "test_results": None,
        "langsmith_evaluation": None,
        "screenshots": [],
        "pipeline_status": None
    }
    
    try:
        # 1. Run Unit Tests
        print("\n1. Running Unit Tests...")
        test_results = await test_generator.run_tests_and_generate_report()
        evaluation_results["test_results"] = test_results
        print(f"Tests completed: {test_results.passed}/{test_results.total_tests} passed")
        
        # 2. Generate LangSmith Evaluation
        print("\n2. Running LangSmith Evaluation...")
        if Config.LANGSMITH_API_KEY:
            # Sample test cases for evaluation
            test_cases = [
                {
                    "query": "What's the weather in London?",
                    "response": "Weather in London: 22°C, partly cloudy with 65% humidity",
                    "query_type": "weather"
                },
                {
                    "query": "What is artificial intelligence?",
                    "response": "Artificial Intelligence (AI) is a branch of computer science that aims to create intelligent machines capable of performing tasks that typically require human intelligence.",
                    "query_type": "document"
                },
                {
                    "query": "Tell me about machine learning",
                    "response": "Machine learning is a subset of AI that enables systems to learn and improve from experience without being explicitly programmed.",
                    "query_type": "document"
                }
            ]
            
            langsmith_results = await evaluator.run_batch_evaluation(test_cases)
            langsmith_report = evaluator.generate_evaluation_report(langsmith_results)
            evaluation_results["langsmith_evaluation"] = langsmith_report
            print(f"LangSmith evaluation completed: Average score {langsmith_report['average_score']:.2f}")
        else:
            print("LangSmith API key not configured, skipping evaluation")
        
        # 3. Generate Screenshots
        print("\n3. Generating Screenshots...")
        
        # Generate evaluation report screenshot
        if evaluation_results["langsmith_evaluation"]:
            screenshot_result = await screenshot_generator.capture_evaluation_report(
                evaluation_results["langsmith_evaluation"]
            )
            evaluation_results["screenshots"].append(screenshot_result)
            print(f"Evaluation report screenshot: {screenshot_result.filename}")
        
        # Generate LangSmith dashboard screenshots (if configured)
        if Config.LANGSMITH_API_KEY:
            try:
                dashboard_screenshots = await screenshot_generator.capture_langsmith_dashboard(
                    "ai-pipeline-project"
                )
                evaluation_results["screenshots"].extend(dashboard_screenshots)
                print(f"LangSmith dashboard screenshots: {len(dashboard_screenshots)} captured")
            except Exception as e:
                print(f"Failed to capture LangSmith screenshots: {str(e)}")
        
        # 4. Get Pipeline Status
        print("\n4. Checking Pipeline Status...")
        pipeline_status = await pipeline.get_pipeline_status()
        evaluation_results["pipeline_status"] = pipeline_status
        print(f"Pipeline status: {pipeline_status['pipeline_status']}")
        
        # 5. Generate Final Report
        print("\n5. Generating Final Evaluation Report...")
        await generate_final_report(evaluation_results)
        
        print("\nEvaluation Complete!")
        print("=" * 60)
        print_summary(evaluation_results)
        
    except Exception as e:
        print(f"Evaluation failed: {str(e)}")
        raise

async def generate_final_report(results):
    """Generate comprehensive final evaluation report."""
    report_dir = "./evaluation_reports"
    Path(report_dir).mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{report_dir}/comprehensive_evaluation_{timestamp}.html"
    
    html_content = generate_evaluation_html(results)
    
    with open(filename, "w", encoding="utf-8") as f:
        f.write(html_content)
    
    print(f"Final report saved to: {filename}")

def generate_evaluation_html(results) -> str:
    """Generate HTML for comprehensive evaluation report."""
    test_results = results["test_results"]
    langsmith_results = results["langsmith_evaluation"]
    pipeline_status = results["pipeline_status"]
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>AI Pipeline Comprehensive Evaluation</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }}
            .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
            h1 {{ color: #2c3e50; text-align: center; margin-bottom: 30px; }}
            h2 {{ color: #34495e; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
            .section {{ margin: 30px 0; padding: 20px; background: #f8f9fa; border-radius: 8px; }}
            .metrics {{ display: flex; justify-content: space-around; flex-wrap: wrap; }}
            .metric {{ text-align: center; padding: 20px; margin: 10px; border-radius: 8px; min-width: 150px; }}
            .metric.success {{ background: #d4edda; color: #155724; }}
            .metric.warning {{ background: #fff3cd; color: #856404; }}
            .metric.info {{ background: #d1ecf1; color: #0c5460; }}
            .metric-value {{ font-size: 2em; font-weight: bold; }}
            .metric-label {{ margin-top: 5px; }}
            .status-indicator {{ display: inline-block; width: 12px; height: 12px; border-radius: 50%; margin-right: 8px; }}
            .status-success {{ background: #28a745; }}
            .status-warning {{ background: #ffc107; }}
            .status-error {{ background: #dc3545; }}
            .screenshot-list {{ list-style: none; padding: 0; }}
            .screenshot-item {{ padding: 10px; margin: 5px 0; background: #e9ecef; border-radius: 5px; }}
            .timestamp {{ text-align: center; color: #666; margin-top: 20px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>AI Pipeline Comprehensive Evaluation Report</h1>
            
            <div class="section">
                <h2>Executive Summary</h2>
                <div class="metrics">
                    <div class="metric {'success' if test_results and test_results.success_rate >= 0.8 else 'warning'}">
                        <div class="metric-value">{f'{test_results.success_rate:.1%}' if test_results else 'N/A'}</div>
                        <div class="metric-label">Test Success Rate</div>
                    </div>
                    <div class="metric {'success' if langsmith_results and langsmith_results['average_score'] >= 0.8 else 'warning'}">
                        <div class="metric-value">{f'{langsmith_results["average_score"]:.2f}' if langsmith_results else 'N/A'}</div>
                        <div class="metric-label">LangSmith Score</div>
                    </div>
                    <div class="metric info">
                        <div class="metric-value">{test_results.total_tests if test_results else 0}</div>
                        <div class="metric-label">Total Tests</div>
                    </div>
                    <div class="metric info">
                        <div class="metric-value">{len(results.get('screenshots', []))}</div>
                        <div class="metric-label">Screenshots</div>
                    </div>
                </div>
            </div>
            
            <div class="section">
                <h2>Test Results</h2>
                {generate_test_summary_html(test_results) if test_results else '<p>No test results available</p>'}
            </div>
            
            <div class="section">
                <h2>LangSmith Evaluation</h2>
                {generate_langsmith_summary_html(langsmith_results) if langsmith_results else '<p>No LangSmith evaluation available</p>'}
            </div>
            
            <div class="section">
                <h2>Pipeline Status</h2>
                {generate_pipeline_status_html(pipeline_status) if pipeline_status else '<p>No pipeline status available</p>'}
            </div>
            
            <div class="section">
                <h2>Generated Screenshots</h2>
                <ul class="screenshot-list">
                    {"".join([f'<li class="screenshot-item">{s.filename} - {s.description}</li>' for s in results.get('screenshots', [])])}
                </ul>
            </div>
            
            <div class="timestamp">Report generated on {results['timestamp']}</div>
        </div>
    </body>
    </html>
    """
    
    return html

def generate_test_summary_html(test_results) -> str:
    """Generate HTML for test results summary."""
    return f"""
    <div class="metrics">
        <div class="metric success">
            <div class="metric-value">{test_results.passed}</div>
            <div class="metric-label">Passed</div>
        </div>
        <div class="metric {'warning' if test_results.failed > 0 else 'success'}">
            <div class="metric-value">{test_results.failed}</div>
            <div class="metric-label">Failed</div>
        </div>
        <div class="metric {'warning' if test_results.errors > 0 else 'success'}">
            <div class="metric-value">{test_results.errors}</div>
            <div class="metric-label">Errors</div>
        </div>
        <div class="metric info">
            <div class="metric-value">{test_results.duration:.2f}s</div>
            <div class="metric-label">Duration</div>
        </div>
    </div>
    """

def generate_langsmith_summary_html(langsmith_results) -> str:
    """Generate HTML for LangSmith evaluation summary."""
    return f"""
    <div class="metrics">
        <div class="metric {'success' if langsmith_results['average_score'] >= 0.8 else 'warning'}">
            <div class="metric-value">{f'{langsmith_results["average_score"]:.2f}'}</div>
            <div class="metric-label">Average Score</div>
        </div>
        <div class="metric info">
            <div class="metric-value">{langsmith_results['total_evaluations']}</div>
            <div class="metric-label">Evaluations</div>
        </div>
        <div class="metric info">
            <div class="metric-value">{f'{langsmith_results["min_score"]:.2f}'}</div>
            <div class="metric-label">Min Score</div>
        </div>
        <div class="metric info">
            <div class="metric-value">{f'{langsmith_results["max_score"]:.2f}'}</div>
            <div class="metric-label">Max Score</div>
        </div>
    </div>
    <p><strong>Score Distribution:</strong> Excellent: {langsmith_results['score_distribution']['excellent']}, 
    Good: {langsmith_results['score_distribution']['good']}, 
    Fair: {langsmith_results['score_distribution']['fair']}, 
    Poor: {langsmith_results['score_distribution']['poor']}</p>
    """

def generate_pipeline_status_html(pipeline_status) -> str:
    """Generate HTML for pipeline status."""
    status_class = "success" if pipeline_status.get("pipeline_status") == "active" else "error"
    status_icon = "✅" if pipeline_status.get("pipeline_status") == "active" else "❌"
    
    return f"""
    <div class="metrics">
        <div class="metric {status_class}">
            <div class="metric-value">{status_icon} {pipeline_status.get('pipeline_status', 'unknown')}</div>
            <div class="metric-label">Pipeline Status</div>
        </div>
        <div class="metric info">
            <div class="metric-value">{pipeline_status.get('vector_database', {}).get('documents_count', 0)}</div>
            <div class="metric-label">Documents</div>
        </div>
        <div class="metric info">
            <div class="metric-value">{pipeline_status.get('vector_database', {}).get('indexed_vectors_count', 0)}</div>
            <div class="metric-label">Vectors</div>
        </div>
    </div>
    """

def print_summary(results):
    """Print evaluation summary to console."""
    print("\nEVALUATION SUMMARY:")
    print("-" * 30)
    
    if results["test_results"]:
        test = results["test_results"]
        print(f"Tests: {test.passed}/{test.total_tests} passed ({test.success_rate:.1%})")
    
    if results["langsmith_evaluation"]:
        langsmith = results["langsmith_evaluation"]
        print(f"LangSmith Score: {langsmith['average_score']:.2f}")
    
    print(f"Screenshots: {len(results.get('screenshots', []))}")
    print(f"Pipeline Status: {results.get('pipeline_status', {}).get('pipeline_status', 'unknown')}")
    
    print("\nGenerated Files:")
    print("-" * 30)
    print("• test_results/ - Detailed test reports")
    print("• screenshots/ - Evaluation screenshots")
    print("• evaluation_reports/ - Comprehensive evaluation report")

if __name__ == "__main__":
    asyncio.run(main())
