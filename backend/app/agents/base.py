import logging
import platform
from typing import Any, Dict, List, Optional

import httpx
import psutil

from ..config import settings

logger = logging.getLogger("sugio_labs.agents.base")


class LocalLLMClient:
    """Local Ollama client with a deterministic offline assistant fallback."""

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url or settings.ollama_base_url
        self.client = httpx.AsyncClient(timeout=60.0)

    async def is_ollama_online(self) -> bool:
        try:
            res = await self.client.get(f"{self.base_url}/api/tags", timeout=2.0)
            return res.status_code == 200
        except Exception:
            return False

    async def list_local_models(self) -> List[str]:
        try:
            res = await self.client.get(f"{self.base_url}/api/tags", timeout=3.0)
            if res.status_code == 200:
                data = res.json()
                return [m["name"] for m in data.get("models", [])]
        except Exception as exc:
            logger.debug("Unable to query Ollama models: %s", exc)
        return []

    def get_hardware_profile(self) -> Dict[str, Any]:
        ram_gb = round(psutil.virtual_memory().total / (1024**3), 1)
        cpu_count = psutil.cpu_count(logical=True) or 1
        os_info = f"{platform.system()} {platform.release()}"

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

    def heuristic_response(self, prompt: str, language: str = "en") -> str:
        """Useful local-only response when Ollama is unavailable."""
        normalized = prompt.lower()

        if language == "ta":
            prefix = "Ollama offline-ஆ இருக்கு. Sugio-வின் local fallback பதில்: "
        elif language == "tanglish":
            prefix = "Ollama offline. Sugio local fallback-la: "
        else:
            prefix = "Ollama is offline, so Sugio is using its built-in local fallback. "

        if any(word in normalized for word in ["architecture", "stack", "design"]):
            return prefix + (
                "Keep the app split into React UI, FastAPI API/services, a relational persistence layer, "
                "and automated tests. Treat request/response schemas as contracts and connect them to the "
                "components, services, database entities, and tests that depend on them."
            )
        if any(word in normalized for word in ["contract", "graph", "schema", "drift"]):
            return prefix + (
                "Use the Contract Graph to trace Requirement → Frontend → API → Backend → Database → Tests. "
                "Before changing a field or endpoint, run Impact Analysis and update every affected contract together."
            )
        if any(word in normalized for word in ["test", "verify", "quality"]):
            return prefix + (
                "Verify changes in layers: schema validation first, backend unit/API tests second, frontend build/tests third, "
                "then Contract Graph drift checks. Create a Git checkpoint before multi-file changes."
            )
        if any(word in normalized for word in ["permission", "safe", "security"]):
            return prefix + (
                "Keep reads low-friction, but require explicit approval for file writes, shell execution, migrations, "
                "network access, and destructive Git operations. Prefer allow-once for unfamiliar actions."
            )
        return prefix + (
            "I can still help with project planning, architecture, contract impact, testing strategy, and safe execution. "
            "Start Ollama when you want free-form model generation."
        )

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.2,
    ) -> str:
        target_model = model or settings.default_model

        if not await self.is_ollama_online():
            return self.heuristic_response(prompt)

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
        except Exception as exc:
            logger.warning("Ollama generation failed; using offline fallback: %s", exc)
            return self.heuristic_response(prompt)

    def get_chat_model(self, model: Optional[str] = None, temperature: float = 0.2):
        from langchain_ollama import ChatOllama

        return ChatOllama(
            base_url=self.base_url,
            model=model or settings.default_model,
            temperature=temperature,
        )


local_llm = LocalLLMClient()
