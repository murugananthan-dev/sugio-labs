import os
import json
import logging
import platform
import psutil
from typing import Dict, Any, Optional, List
import httpx

from ..config import settings

logger = logging.getLogger("sugio_labs.agents.base")


class LocalLLMClient:
    """
    Client for Local LLM execution via Ollama.
    Supports offline fallback, hardware detection, model recommendations, and structured output parsing.
    """

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url or settings.ollama_base_url
        self.client = httpx.AsyncClient(timeout=60.0)

    async def is_ollama_online(self) -> bool:
        """Checks if local Ollama daemon is reachable."""
        try:
            res = await self.client.get(f"{self.base_url}/api/tags", timeout=2.0)
            return res.status_code == 200
        except Exception:
            return False

    async def list_local_models(self) -> List[str]:
        """Lists downloaded models in Ollama."""
        try:
            res = await self.client.get(f"{self.base_url}/api/tags", timeout=3.0)
            if res.status_code == 200:
                data = res.json()
                return [m["name"] for m in data.get("models", [])]
        except Exception as e:
            logger.warning(f"Unable to query Ollama models: {e}")
        return []

    def get_hardware_profile(self) -> Dict[str, Any]:
        """Detects system RAM, CPU cores, and OS to recommend optimal local model sizes."""
        ram_gb = round(psutil.virtual_memory().total / (1024**3), 1)
        cpu_count = psutil.cpu_count(logical=True)
        os_info = f"{platform.system()} {platform.release()}"

        # Recommendation logic
        if ram_gb >= 16:
            rec_model = "llama3:8b or qwen2.5-coder:7b (Q4_K_M)"
            rec_tier = "High Performance (7B - 8B Models)"
        elif ram_gb >= 8:
            rec_model = "qwen2.5-coder:3b or phi3:mini (Q4_K_M)"
            rec_tier = "Standard Performance (3B - 4B Models)"
        else:
            rec_model = "tinyllama:1.1b or qwen2.5-coder:1.5b"
            rec_tier = "Lightweight / Fallback"

        return {
            "ram_gb": ram_gb,
            "cpu_cores": cpu_count,
            "os": os_info,
            "recommended_model": rec_model,
            "recommended_tier": rec_tier,
        }

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.2,
    ) -> str:
        """
        Sends generation request to local Ollama.
        Raises ConnectionError if Ollama is unreachable.
        """
        target_model = model or settings.default_model

        if not await self.is_ollama_online():
            raise ConnectionError(f"Ollama is unreachable at {self.base_url}. Cannot proceed with local AI generation.")

        try:
            payload = {
                "model": target_model,
                "prompt": prompt,
                "system": system_prompt or "You are Sugio Labs, an expert AI software architect and full-stack developer.",
                "stream": False,
                "options": {"temperature": temperature},
            }
            res = await self.client.post(f"{self.base_url}/api/generate", json=payload, timeout=45.0)
            res.raise_for_status()
            return res.json().get("response", "").strip()
        except Exception as e:
            logger.error(f"Ollama generation failed: {e}.")
            raise ConnectionError(f"Failed to generate using local Ollama model {target_model}: {e}")

    def get_chat_model(self, model: Optional[str] = None, temperature: float = 0.2):
        """
        Returns a LangChain-compatible ChatOllama instance connected to the local Ollama daemon.
        """
        from langchain_ollama import ChatOllama
        target_model = model or settings.default_model
        return ChatOllama(
            base_url=self.base_url,
            model=target_model,
            temperature=temperature
        )


local_llm = LocalLLMClient()
