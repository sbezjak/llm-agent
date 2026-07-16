import json
import logging

import httpx

from .base import AssistantMessage, Provider, ToolCall

log = logging.getLogger(__name__)


class OllamaProvider(Provider):
    def __init__(
        self,
        model: str = "llama3.2",
        base_url: str = "http://localhost:11434",
        timeout: float = 60.0,
    ):
        self.model = model
        self.base_url = base_url
        self.timeout = timeout

    async def generate(self, prompt: str) -> str:
        log.info("PROMPT to %s:\n%s", self.model, prompt)
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.post(
                f"{self.base_url}/api/generate",
                json={"model": self.model, "prompt": prompt, "stream": False},
            )
            r.raise_for_status()
            out = r.json()["response"]
        log.info("RESPONSE from %s:\n%s", self.model, out)
        return out

    async def chat(self, messages: list[dict], tools: list[dict]) -> AssistantMessage:
        log.info("CHAT REQUEST to %s:\n%s", self.model, json.dumps(messages, indent=2))
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.post(
                f"{self.base_url}/api/chat",
                json={"model": self.model, "messages": messages, "tools": tools, "stream": False},
            )
            r.raise_for_status()
            message = r.json()["message"]
        log.info("CHAT RESPONSE from %s:\n%s", self.model, json.dumps(message, indent=2))
        tool_calls = tuple(
            ToolCall(name=c["function"]["name"], args=c["function"].get("arguments") or {})
            for c in message.get("tool_calls") or ()
        )
        return AssistantMessage(content=message.get("content") or "", tool_calls=tool_calls)
