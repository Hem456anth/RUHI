"""Weather tool — OpenWeatherMap.

Ported from ``Ruhi/features/weather.py``: async, typed, settings-driven.
"""
from __future__ import annotations

from dataclasses import dataclass

import httpx

from shared.config import settings
from shared.tools.errors import ToolError

_BASE_URL = "https://api.openweathermap.org/data/2.5/weather"


@dataclass
class WeatherReport:
    city: str
    description: str
    temp_c: float
    pressure_hpa: int
    humidity_pct: int
    wind_kmh: float

    def to_sentence(self) -> str:
        return (
            f"Weather in {self.city}: {self.description}, "
            f"{self.temp_c}°C, humidity {self.humidity_pct}%, "
            f"wind {self.wind_kmh} km/h, pressure {self.pressure_hpa} hPa."
        )


async def fetch_weather(city: str) -> WeatherReport:
    settings.require("openweather_api_key")
    params = {"q": city, "appid": settings.openweather_api_key, "units": "metric"}
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(_BASE_URL, params=params)
    if resp.status_code == 404:
        raise ToolError(f"City not found: {city!r}", code="not_found")
    if resp.status_code != 200:
        raise ToolError(f"OpenWeather returned {resp.status_code}", code="upstream")
    data = resp.json()
    main = data["main"]
    return WeatherReport(
        city=city,
        description=data["weather"][0]["description"],
        temp_c=main["temp"],
        pressure_hpa=main["pressure"],
        humidity_pct=main["humidity"],
        wind_kmh=data["wind"]["speed"] * 3.6,
    )
