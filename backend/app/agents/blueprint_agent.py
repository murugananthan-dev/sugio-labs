import logging
from langchain_core.messages import SystemMessage, HumanMessage
from ..models.schemas import (
    AppState,
    ProjectBlueprint,
)
from .base import local_llm

logger = logging.getLogger("sugio_labs.agents.blueprint")

class BlueprintAgent:
    """
    Architecture/Blueprint Agent.
    Takes structured requirements and generates a full Project Blueprint.
    """
    def __init__(self):
        self.system_prompt = (
            "You are Sugio Labs, a senior Software Architect. "
            "Your task is to take the provided Requirements Specification and generate a complete, "
            "structured Project Blueprint. "
            "Include technical stack details, database schema recommendations, backend and frontend module paths, "
            "and API endpoint structures. Keep it professional and complete."
        )

    def process(self, state: AppState) -> AppState:
        logger.info("BlueprintAgent generating architecture blueprint...")
        
        chat_model = local_llm.get_chat_model(temperature=0.2)
        structured_llm = chat_model.with_structured_output(ProjectBlueprint)
        
        req_json = state["requirements"].model_dump_json() if state.get("requirements") else "{}"
        
        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=f"Here is the finalized Requirement Specification. Generate the blueprint.\n\n{req_json}")
        ]
        
        try:
            blueprint: ProjectBlueprint = structured_llm.invoke(messages)
            blueprint.approved = False
            state["blueprint"] = blueprint
            state["approval_status"] = "WAITING_FOR_APPROVAL"
        except Exception as e:
            logger.error(f"Blueprint generation failed: {e}")
            if "errors" not in state:
                state["errors"] = []
            state["errors"].append(str(e))
            state["approval_status"] = "ERROR"
            
        return state

blueprint_agent = BlueprintAgent()
