import asyncio
import os
import sys
import time
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from pathlib import Path
import structlog
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from PIL import Image
import io

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from src.config import Config
except ImportError:
    print("Warning: Could not import Config, continuing without it")
    Config = None

logger = structlog.get_logger()

@dataclass
class ScreenshotResult:
    """Screenshot result structure."""
    filename: str
    timestamp: str
    description: str
    success: bool
    error: Optional[str] = None

class ScreenshotGenerator:
    """Generate screenshots of LangSmith dashboard and evaluation results."""
    
    def __init__(self):
        self.driver = None
        self.screenshots_dir = "./screenshots"
        self._ensure_screenshots_dir()
    
    def _ensure_screenshots_dir(self):
        """Create screenshots directory if it doesn't exist."""
        if not os.path.exists(self.screenshots_dir):
            os.makedirs(self.screenshots_dir)
    
    def _setup_driver(self) -> webdriver.Chrome:
        """Setup Chrome WebDriver for screenshot generation."""
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920,1080")
        
        try:
            driver = webdriver.Chrome(options=options)
            return driver
        except Exception as e:
            logger.error(f"Failed to setup WebDriver: {str(e)}")
            raise
    
    async def capture_langsmith_dashboard(self, project_name: str, output_dir: str = "./screenshots") -> List[ScreenshotResult]:
        """
        Capture screenshots of LangSmith dashboard.
        
        Args:
            project_name: LangSmith project name
            output_dir: Directory to save screenshots
            
        Returns:
            List of screenshot results
        """
        if not Config or not Config.LANGSMITH_API_KEY:
            print("Error: LangSmith API key not configured")
            return []
        
        results = []
        self.driver = self._setup_driver()
        
        try:
            # Navigate to LangSmith
            self.driver.get("https://smith.langchain.com")
            await asyncio.sleep(3)
            
            # Login (if needed)
            await self._login_to_langsmith()
            
            # Navigate to project
            await self._navigate_to_project(project_name)
            
            # Capture different views
            screenshots = [
                ("dashboard", "Main dashboard view"),
                ("traces", "Query traces"),
                ("evaluations", "Evaluation results"),
                ("metrics", "Performance metrics")
            ]
            
            for view, description in screenshots:
                result = await self._capture_view(view, description, output_dir)
                results.append(result)
                await asyncio.sleep(2)
            
        except Exception as e:
            print(f"Error capturing LangSmith screenshots: {str(e)}")
            results.append(ScreenshotResult(
                filename="error",
                timestamp=time.strftime("%Y%m%d_%H%M%S"),
                description="Error capturing screenshots",
                success=False,
                error=str(e)
            ))
        
        finally:
            if self.driver:
                self.driver.quit()
        
        return results
    
    async def _login_to_langsmith(self):
        """Login to LangSmith if authentication is required."""
        try:
            # Check if already logged in
            if "smith.langchain.com" in self.driver.current_url:
                # Look for login button or sign-in elements
                login_elements = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'Sign in') or contains(text(), 'Login')]")
                if not login_elements:
                    print("Already logged in to LangSmith")
                    return
                
            # For demo purposes, we'll assume manual login is required
            print("Please login to LangSmith manually in the browser window")
            await asyncio.sleep(30)  # Wait for manual login
            
        except Exception as e:
            print(f"Login process failed: {str(e)}")
    
    async def _navigate_to_project(self, project_name: str):
        """Navigate to the specified project."""
        try:
            # Look for project selector or navigation
            project_url = f"https://smith.langchain.com/o/{Config.LANGSMITH_ORGANIZATION}/projects/{project_name}"
            self.driver.get(project_url)
            await asyncio.sleep(3)
            
        except Exception as e:
            print(f"Failed to navigate to project {project_name}: {str(e)}")
            raise
    
    async def _capture_view(self, view_name: str, description: str, output_dir: str) -> ScreenshotResult:
        """Capture a specific view of the dashboard."""
        try:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"langsmith_{view_name}_{timestamp}.png"
            filepath = os.path.join(output_dir, filename)
            
            # Wait for page to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Take screenshot
            self.driver.save_screenshot(filepath)
            
            # Resize and optimize image
            await self._optimize_screenshot(filepath)
            
            return ScreenshotResult(
                filename=filename,
                timestamp=timestamp,
                description=description,
                success=True
            )
            
        except Exception as e:
            print(f"Failed to capture {view_name}: {str(e)}")
            return ScreenshotResult(
                filename=f"error_{view_name}_{timestamp}",
                timestamp=time.strftime("%Y%m%d_%H%M%S"),
                description=description,
                success=False,
                error=str(e)
            )
    
    async def _optimize_screenshot(self, filepath: str):
        """Optimize screenshot for better quality and smaller size."""
        try:
            with Image.open(filepath) as img:
                # Resize if too large
                if img.width > 1920:
                    ratio = 1920 / img.width
                    new_size = (1920, int(img.height * ratio))
                    img = img.resize(new_size, Image.Resampling.LANCZOS)
                
                # Save with optimization
                img.save(filepath, "PNG", optimize=True, quality=85)
                
        except Exception as e:
            print(f"Failed to optimize screenshot: {str(e)}")
    
    async def capture_evaluation_report(self, evaluation_results: Dict[str, Any], output_dir: str = "./screenshots") -> ScreenshotResult:
        """
        Generate and capture evaluation report visualization.
        
        Args:
            evaluation_results: Results from LangSmith evaluation
            output_dir: Directory to save screenshot
            
        Returns:
            Screenshot result
        """
        try:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"evaluation_report_{timestamp}.png"
            filepath = os.path.join(output_dir, filename)
            
            # Create a simple HTML report
            html_content = self._generate_evaluation_html(evaluation_results)
            
            # Save HTML file
            html_file = os.path.join(output_dir, f"evaluation_report_{timestamp}.html")
            with open(html_file, 'w') as f:
                f.write(html_content)
            
            # Open in browser and capture screenshot
            self.driver = self._setup_driver()
            self.driver.get(f"file://{os.path.abspath(html_file)}")
            await asyncio.sleep(2)
            
            self.driver.save_screenshot(filepath)
            await self._optimize_screenshot(filepath)
            
            return ScreenshotResult(
                filename=filename,
                timestamp=timestamp,
                description="Evaluation report visualization",
                success=True
            )
            
        except Exception as e:
            print(f"Failed to capture evaluation report: {str(e)}")
            return ScreenshotResult(
                filename=f"error_evaluation_{timestamp}",
                timestamp=time.strftime("%Y%m%d_%H%M%S"),
                description="Evaluation report visualization",
                success=False,
                error=str(e)
            )
        
        finally:
            if self.driver:
                self.driver.quit()
    
    def _generate_evaluation_html(self, results: Dict[str, Any]) -> str:
        """Generate HTML content for evaluation report."""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>AI Pipeline Evaluation Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }}
                .container {{ max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                h1 {{ color: #2c3e50; text-align: center; margin-bottom: 30px; }}
                .metric {{ display: inline-block; margin: 20px; padding: 20px; background: #ecf0f1; border-radius: 8px; text-align: center; min-width: 150px; }}
                .metric-value {{ font-size: 2em; font-weight: bold; color: #3498db; }}
                .metric-label {{ color: #7f8c8d; margin-top: 5px; }}
                .chart {{ margin: 30px 0; padding: 20px; background: #f8f9fa; border-radius: 8px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>AI Pipeline Evaluation Report</h1>
                
                <div class="metric">
                    <div class="metric-value">{results.get('average_score', 0):.2f}</div>
                    <div class="metric-label">Average Score</div>
                </div>
                
                <div class="metric">
                    <div class="metric-value">{results.get('total_evaluations', 0)}</div>
                    <div class="metric-label">Total Evaluations</div>
                </div>
                
                <div class="metric">
                    <div class="metric-value">{results.get('min_score', 0):.2f}</div>
                    <div class="metric-label">Min Score</div>
                </div>
                
                <div class="metric">
                    <div class="metric-value">{results.get('max_score', 0):.2f}</div>
                    <div class="metric-label">Max Score</div>
                </div>
                
                <div class="chart">
                    <h3>Score Distribution</h3>
                    <p>Excellent: {results.get('score_distribution', {}).get('excellent', 0)}</p>
                    <p>Good: {results.get('score_distribution', {}).get('good', 0)}</p>
                    <p>Fair: {results.get('score_distribution', {}).get('fair', 0)}</p>
                    <p>Poor: {results.get('score_distribution', {}).get('poor', 0)}</p>
                </div>
                
                <div style="text-align: center; margin-top: 30px; color: #7f8c8d;">
                    Generated on {time.strftime("%Y-%m-%d %H:%M:%S")}
                </div>
            </div>
        </body>
        </html>
        """
        return html

async def main():
    """Example usage of screenshot generator."""
    generator = ScreenshotGenerator()
    
    # Example evaluation results
    sample_results = {
        "total_evaluations": 10,
        "average_score": 0.85,
        "min_score": 0.7,
        "max_score": 0.95,
        "score_distribution": {
            "excellent": 3,
            "good": 5,
            "fair": 2,
            "poor": 0
        }
    }
    
    # Capture evaluation report
    result = await generator.capture_evaluation_report(sample_results)
    print(f"Evaluation report screenshot: {result.filename}")
    
    # Capture LangSmith dashboard (if configured)
    if Config and Config.LANGSMITH_API_KEY:
        screenshots = await generator.capture_langsmith_dashboard("ai-pipeline-project")
        for screenshot in screenshots:
            print(f"Screenshot: {screenshot.filename} - {screenshot.description}")

if __name__ == "__main__":
    asyncio.run(main())
