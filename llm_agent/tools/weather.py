from .base import Tool

_DEFAULT_CONDITIONS = {
    "ljubljana": "Clear, 28 °C, wind 5 km/h from the northwest.",
    "sydney": "Showers, 16 °C, wind 22 km/h from the southeast.",
    "tokyo": "Overcast, 21 °C, humidity 88%.",
    "london": "Light rain, 14 °C, wind 12 km/h.",
}


def weather_tool(conditions: dict[str, str] | None = None) -> Tool:
    """Canned city -> report lookup. Tests inject altered or conflicting
    reports by passing their own conditions dict; an unknown city raises,
    the mock analog of a real weather API's 404."""
    reports = _DEFAULT_CONDITIONS if conditions is None else conditions

    async def get_weather(city: str) -> str:
        report = reports.get(city.strip().lower())
        if report is None:
            raise ValueError(f"no weather data for city {city!r}")
        return report

    return Tool(
        name="get_weather",
        description="Get the current weather report for a city.",
        parameters={
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "City name, e.g. 'Ljubljana'"}
            },
            "required": ["city"],
        },
        handler=get_weather,
    )


WEATHER = weather_tool()
