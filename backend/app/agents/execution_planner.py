import logging
from typing import Dict, Any, List
from langchain_core.messages import SystemMessage, HumanMessage
from ..models.schemas import AppState, ExecutionPlan
from .base import local_llm

logger = logging.getLogger("sugio_labs.agents.execution_planner")

class ExecutionPlannerAgent:
    def __init__(self):
        self.system_prompt = (
            "You are an expert AI Execution Planner. "
            "Your job is to read an approved Project Blueprint and generate a structured ExecutionPlan. "
            "Break down the implementation into discrete, safe, logical ExecutionSteps. "
            "Do NOT write actual code files yet. Just plan the sequence of actions. "
            "Make sure to identify files to read, files to modify, and shell commands required for validation. "
            "Keep the risk level accurate based on the destructiveness of the operation."
        )

    def process(self, state: AppState) -> AppState:
        logger.info("ExecutionPlannerAgent generating execution plan...")
        
        if not state.get("blueprint"):
            raise ValueError("No blueprint found in state.")
            
        chat_model = local_llm.get_chat_model(temperature=0.1)
        structured_llm = chat_model.with_structured_output(ExecutionPlan)
        
        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=f"Please generate an execution plan for this blueprint:\n{state['blueprint'].model_dump_json(indent=2)}")
        ]
        
        plan = structured_llm.invoke(messages)
        
        state["execution_plan"] = plan
        state["execution_approval_status"] = "WAITING_FOR_EXECUTION_APPROVAL"
        
        # Initialize execution tracking fields
        state["current_step_index"] = 0
        state["execution_results"] = []
        
        return state

execution_planner = ExecutionPlannerAgent()
