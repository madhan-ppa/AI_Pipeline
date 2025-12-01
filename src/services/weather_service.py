import asyncio
import aiohttp
from typing import Dict, Any, Optional
from dataclasses import dataclass
import structlog

from src.config import Config

logger = structlog.get_logger()

@dataclass
class WeatherData:
    city: str
    temperature: float
    description: str
    humidity: int
    wind_speed: float
    feels_like: float
    timestamp: str

class WeatherService:
    
    def __init__(self):
        self.api_key = Config.OPENWEATHERMAP_API_KEY
        self.base_url = Config.OPENWEATHERMAP_BASE_URL
        self.timeout = Config.REQUEST_TIMEOUT
    
    async def get_current_weather(self, city: str) -> Optional[WeatherData]:
        if not self.api_key:
            logger.error("OpenWeatherMap API key not configured")
            return None
        
        url = f"{self.base_url}/weather"
        params = {
            "q": city,
            "appid": self.api_key,
            "units": "metric"
        }
        
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._parse_weather_data(data, city)
                    elif response.status == 404:
                        logger.warning(f"City not found: {city}")
                        return None
                    else:
                        logger.error(f"API request failed with status {response.status}: {await response.text()}")
                        return None
        
        except asyncio.TimeoutError:
            logger.error(f"Timeout while fetching weather for {city}")
            return None
        except Exception as e:
            logger.error(f"Error fetching weather data: {str(e)}")
            return None
    
    def _parse_weather_data(self, data: Dict[str, Any], city: str) -> WeatherData:
        main = data.get("main", {})
        weather = data.get("weather", [{}])[0]
        wind = data.get("wind", {})
        
        return WeatherData(
            city=city,
            temperature=main.get("temp", 0),
            description=weather.get("description", "No description"),
            humidity=main.get("humidity", 0),
            wind_speed=wind.get("speed", 0),
            feels_like=main.get("feels_like", 0),
            timestamp=data.get("dt", "")
        )
    
    def format_weather_response(self, weather_data: WeatherData) -> str:
        return f"""Weather in {weather_data.city}:
- Temperature: {weather_data.temperature}°C (feels like {weather_data.feels_like}°C)
- Description: {weather_data.description.capitalize()}
- Humidity: {weather_data.humidity}%
- Wind Speed: {weather_data.wind_speed} m/s"""
