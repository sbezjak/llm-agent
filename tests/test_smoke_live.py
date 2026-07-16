import pytest

from llm_agent.providers.ollama import OllamaProvider
from llm_agent.runners.run import SUT_MODEL


@pytest.mark.live
async def test_live_backend_responds():
    out = await OllamaProvider(model=SUT_MODEL).generate("Say exactly the word: ok")
    assert isinstance(out, str) and len(out) > 0
