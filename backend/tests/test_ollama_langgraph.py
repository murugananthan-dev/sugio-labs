import pytest
from unittest.mock import AsyncMock, patch

from app.agents.base import LocalLLMClient
from app.agents.supervisor import chat_graph


@pytest.mark.asyncio
async def test_ollama_offline_uses_local_fallback():
    client = LocalLLMClient(base_url="http://invalid.local:9999")

    with patch.object(client, "is_ollama_online", new_callable=AsyncMock) as mock_online:
        mock_online.return_value = False
        response = await client.generate("Explain the contract graph")

    assert "fallback" in response.lower()
    assert "contract" in response.lower()


def test_langgraph_supervisor_compiles():
    assert chat_graph is not None
    assert "agent" in chat_graph.nodes
