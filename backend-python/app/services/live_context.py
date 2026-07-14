"""Phase 2 external context enrichment: Open-Meteo and GDACS feeds."""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
import httpx

from app.schemas.relief import GDACSAlert, WeatherData

logger = logging.getLogger(__name__)

# Weather code descriptions from WMO Weather Interpretation Codes
WEATHER_CODE_MAP = {
    0: "Clear Sky",
    1: "Mainly Clear",
    2: "Partly Cloudy",
    3: "Overcast",
    45: "Foggy",
    48: "Depositing Rime Fog",
    51: "Light Drizzle",
    53: "Moderate Drizzle",
    55: "Dense Drizzle",
    61: "Light Rain",
    63: "Moderate Rain",
    65: "Heavy Rain",
    71: "Slight Snowfall",
    73: "Moderate Snowfall",
    75: "Heavy Snowfall",
    80: "Slight Rain Showers",
    81: "Moderate Rain Showers",
    82: "Violent Rain Showers",
    95: "Thunderstorm",
    96: "Thunderstorm with Hail",
    99: "Thunderstorm with Heavy Hail",
}


class LiveContextService:
    """Fetch real-time weather and global disaster alerts with robust static fallbacks."""

    def __init__(self) -> None:
        self.fallback_weather = WeatherData(
            temperature=14.5,
            weathercode=3,
            windspeed=12.4,
            description="Overcast",
        )
        self.fallback_alerts = [
            GDACSAlert(
                title="Tropical Cyclone Emnati-22 Alert in Madagascar",
                description="Red Alert for Tropical Cyclone Emnati-22 affecting Madagascar. Speed up to 180 km/h.",
                link="https://www.gdacs.org",
            ),
            GDACSAlert(
                title="Earthquake M 5.8 Alert in Western Turkey",
                description="Green Alert for Earthquake M 5.8 in Western Turkey. Minor damage expected.",
                link="https://www.gdacs.org",
            ),
            GDACSAlert(
                title="Flooding Alert in Jakarta, Indonesia",
                description="Orange Alert for Flooding in Jakarta. Heavy seasonal monsoon rains ongoing.",
                link="https://www.gdacs.org",
            ),
        ]

    async def fetch_weather(self) -> WeatherData:
        """Fetch current Central London weather from the Open-Meteo API."""

        url = "https://api.open-meteo.com/v1/forecast?latitude=51.5074&longitude=-0.1278&current_weather=true"
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=3.0)
                if response.status_code == 200:
                    data = response.json().get("current_weather", {})
                    code = int(data.get("weathercode", 3))
                    return WeatherData(
                        temperature=float(data.get("temperature", 14.5)),
                        weathercode=code,
                        windspeed=float(data.get("windspeed", 12.4)),
                        description=WEATHER_CODE_MAP.get(code, "Unknown Conditions"),
                    )
        except Exception as exc:
            logger.warning(f"Failed to fetch live weather, using fallback: {exc}")

        return self.fallback_weather

    async def fetch_gdacs_alerts(self) -> list[GDACSAlert]:
        """Fetch and parse live global disaster alerts from GDACS RSS feed."""

        url = "https://www.gdacs.org/xml/rss.xml"
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=3.0)
                if response.status_code == 200:
                    root = ET.fromstring(response.content)
                    alerts = []
                    for item in root.findall(".//item"):
                        title_el = item.find("title")
                        desc_el = item.find("description")
                        link_el = item.find("link")
                        
                        title = title_el.text if title_el is not None else ""
                        desc = desc_el.text if desc_el is not None else ""
                        link = link_el.text if link_el is not None else "https://www.gdacs.org"

                        # Strip HTML tags from description if present
                        if desc and "<" in desc:
                            # Basic string cleanup for display
                            import re
                            desc = re.sub('<[^<]+?>', '', desc)

                        if title:
                            alerts.append(GDACSAlert(title=title, description=desc, link=link))
                    
                    if alerts:
                        return alerts[:5]  # Limit to 5 alerts for a clean dashboard feed
        except Exception as exc:
            logger.warning(f"Failed to fetch GDACS alerts, using fallback: {exc}")

        return self.fallback_alerts


live_context_service = LiveContextService()
