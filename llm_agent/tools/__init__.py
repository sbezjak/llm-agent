from .base import Tool, ToolRegistry
from .calculator import CALCULATOR
from .file_reader import FILE_READER, file_reader_tool
from .injection import with_delay, with_error
from .weather import WEATHER, weather_tool
from .web_search import WEB_SEARCH, web_search_tool
from .write_file import write_file_tool


def default_registry() -> ToolRegistry:
    return ToolRegistry([CALCULATOR, FILE_READER, WEATHER, WEB_SEARCH])


__all__ = [
    "CALCULATOR",
    "FILE_READER",
    "WEATHER",
    "WEB_SEARCH",
    "Tool",
    "ToolRegistry",
    "default_registry",
    "file_reader_tool",
    "weather_tool",
    "web_search_tool",
    "with_delay",
    "with_error",
    "write_file_tool",
]
