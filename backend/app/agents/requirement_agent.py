import logging
from typing import List, Dict, Any, Optional
from langchain_core.messages import SystemMessage, HumanMessage
from ..models.schemas import (
    PlanningState,
    RequirementSpec,
    PartialRequirementExtraction,
)
from .base import local_llm

logger = logging.getLogger("sugio_labs.agents.requirement")

class RequirementAgent:
    """
    Requirement Gathering Interview Agent using LLM structured output.
    Analyzes conversation history to extract requirements, identify missing info, and ask the next question.
    """
    def __init__(self):
        self.system_prompt = (
            "You are Sugio Labs, an expert AI software architect and development agent. "
            "Your job is to interview the user about their project idea and extract requirements. "
            "You must ask ONE clear, focused question at a time to fill in missing details. "
            "Do NOT ask multiple questions at once. "
            "If the user speaks in Tamil or Tanglish, your 'next_question' MUST be in the same language, but "
            "keep the extracted spec fields in English. "
            "If the requirements are sufficient to build a comprehensive backend and frontend architecture (meaning you "
            "know the domain, features, stack preferences, and basic roles), set 'is_complete' to True and 'next_question' to empty. "
            "Do not demand excessive detail. Aim for a solid MVP foundation."
        )

    def process(self, state: PlanningState) -> PlanningState:
        """Processes the state to extract requirements and determine the next question."""
        logger.info("RequirementAgent processing current state...")
        
        chat_model = local_llm.get_chat_model(temperature=0.1)
        structured_llm = chat_model.with_structured_output(PartialRequirementExtraction)
        
        messages = [SystemMessage(content=self.system_prompt)]
        
        # Add current known requirements context
        if state.get("requirements"):
            req_context = f"Current extracted requirements: {state['requirements'].model_dump_json()}"
            messages.append(SystemMessage(content=req_context))
            
        # Add conversation history
        for msg in state.get("messages", []):
            messages.append(msg)
            
        try:
            extraction: PartialRequirementExtraction = structured_llm.invoke(messages)
            
            # Update state with newly extracted info
            state["requirements"] = extraction.extracted_spec
            state["requirements_complete"] = extraction.is_complete
            
            if not extraction.is_complete:
                state["current_question"] = extraction.next_question
                
        except Exception as e:
            logger.error(f"Requirement extraction failed: {e}")
            if "errors" not in state:
                state["errors"] = []
            state["errors"].append(str(e))
            state["current_question"] = "I encountered an error analyzing your request. Could you please clarify your last point?"
            
        return state

requirement_agent = RequirementAgent()
