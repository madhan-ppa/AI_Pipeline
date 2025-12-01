import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from src.services.weather_service import WeatherService, WeatherData

class TestWeatherService:
    
    @pytest.fixture
    def weather_service(self):
        return WeatherService()
    
    @pytest.mark.asyncio
    async def test_get_current_weather_success(self, weather_service):
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = Mock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={
                "main": {"temp": 22.5, "feels_like": 24.0, "humidity": 65},
                "weather": [{"description": "partly cloudy"}],
                "wind": {"speed": 3.5},
                "name": "London"
            })
            mock_get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
            
            result = await weather_service.get_current_weather("London")
            
            assert result is not None
            assert result.city == "London"
            assert result.temperature == 22.5
            assert result.description == "partly cloudy"
    
    @pytest.mark.asyncio
    async def test_get_current_weather_api_error(self, weather_service):
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = Mock()
            mock_response.status = 404
            mock_get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
            
            result = await weather_service.get_current_weather("InvalidCity")
            
            assert result is None
    
    def test_format_weather_response(self, weather_service):
        weather_data = WeatherData(
            city="London",
            temperature=22.5,
            feels_like=24.0,
            description="partly cloudy",
            humidity=65,
            wind_speed=3.5,
            timestamp="2024-01-01T12:00:00Z"
        )
        
        response = weather_service.format_weather_response(weather_data)
        
        assert "London" in response
        assert "22.5°C" in response
        assert "Partly cloudy" in response
        assert "65%" in response
