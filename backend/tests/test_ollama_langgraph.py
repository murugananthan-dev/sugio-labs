import pytest
import httpx
from httpx import Response
from unittest.mock import patch, AsyncMock
from app.agents.base import LocalLLMClient
from app.agents.supervisor import app_graph as planning_graph

@pytest.mark.asyncio
async def test_ollama_offline_raises_error():
    """Test that when Ollama is unreachable, a ConnectionError is strictly raised (no fallback)."""
    client = LocalLLMClient(base_url="http://invalid.local:9999")
    
    with patch.object(client, "is_ollama_online", new_callable=AsyncMock) as mock_online:
        mock_online.return_value = False
        
        with pytest.raises(ConnectionError) as exc:
            await client.generate("Hello world")
            
        assert "Ollama is unreachable" in str(exc.value)

def test_langgraph_supervisor_compiles():
    """Test that the LangGraph state graph compiles correctly."""
    # Should not raise any Graph compilation errors
    assert planning_graph is not None
    
    # We can inspect the graph to ensure nodes exist
    nodes = planning_graph.nodes
    assert "requirement_node" in nodes
    assert "blueprint_node" in nodes
