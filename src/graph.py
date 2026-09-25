"""
LangGraph State Machine Compilation for Agentic AI STLC Pipeline.

Compiles the 6-stage pipeline into an executable LangGraph workflow.
"""

import logging
from typing import Dict, Any, Literal

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from src.state import AgenticSTLCState
from src.nodes.rag_retrieval import rag_retrieval_node
from src.nodes.agent1_test_author import agent1_test_author_node
from src.nodes.agent2_script_gen import agent2_script_gen_node
from src.nodes.agent2b_mcp_heal import agent2b_mcp_heal_node
from src.nodes.agent3_cicd_trigger import agent3_cicd_trigger_node
from src.nodes.agent4_defect_logger import agent4_defect_logger_node

logger = logging.getLogger(__name__)


def should_continue(state: AgenticSTLCState) -> Literal["continue", "end"]:
    """
    Determine if pipeline should continue or end.
    
    Args:
        state: Current pipeline state
        
    Returns:
        "continue" to proceed to next stage, "end" to terminate
    """
    if state["status"] == "failed":
        logger.info(f"[{state['run_id']}] Pipeline failed, ending")
        return "end"
    
    if state["current_stage"] == "failure_analysis":
        logger.info(f"[{state['run_id']}] Pipeline completed all stages")
        state["status"] = "completed"
        return "end"
    
    return "continue"


def get_next_stage(state: AgenticSTLCState) -> str:
    """
    Determine the next stage based on current stage.
    
    Args:
        state: Current pipeline state
        
    Returns:
        Name of next node to execute
    """
    stage_map = {
        "initialized": "rag_retrieval",
        "rag_retrieval": "test_authoring",
        "test_authoring": "script_generation",
        "script_generation": "selector_healing",
        "selector_healing": "cicd_execution",
        "cicd_execution": "failure_analysis",
        "failure_analysis": "end",
    }
    return stage_map.get(state["current_stage"], "end")


def create_pipeline_graph() -> StateGraph:
    """
    Create and compile the LangGraph state machine for the STLC Pipeline.
    
    Returns:
        Compiled StateGraph ready for execution
    """
    # Create graph with state schema
    workflow = StateGraph(AgenticSTLCState)
    
    # Add nodes for each stage
    workflow.add_node("rag_retrieval", rag_retrieval_node)
    workflow.add_node("test_authoring", agent1_test_author_node)
    workflow.add_node("script_generation", agent2_script_gen_node)
    workflow.add_node("selector_healing", agent2b_mcp_heal_node)
    workflow.add_node("cicd_execution", agent3_cicd_trigger_node)
    workflow.add_node("failure_analysis", agent4_defect_logger_node)
    
    # Set entry point
    workflow.set_entry_point("rag_retrieval")
    
    # Add conditional edges for sequential execution
    workflow.add_conditional_edges(
        "rag_retrieval",
        should_continue,
        {
            "continue": "test_authoring",
            "end": END,
        }
    )
    
    workflow.add_conditional_edges(
        "test_authoring",
        should_continue,
        {
            "continue": "script_generation",
            "end": END,
        }
    )
    
    workflow.add_conditional_edges(
        "script_generation",
        should_continue,
        {
            "continue": "selector_healing",
            "end": END,
        }
    )
    
    workflow.add_conditional_edges(
        "selector_healing",
        should_continue,
        {
            "continue": "cicd_execution",
            "end": END,
        }
    )
    
    workflow.add_conditional_edges(
        "cicd_execution",
        should_continue,
        {
            "continue": "failure_analysis",
            "end": END,
        }
    )
    
    workflow.add_conditional_edges(
        "failure_analysis",
        should_continue,
        {
            "continue": END,
            "end": END,
        }
    )
    
    # Compile with memory checkpointing
    checkpointer = MemorySaver()
    app = workflow.compile(checkpointer=checkpointer)
    
    logger.info("LangGraph pipeline compiled successfully")
    return app


# Compiled graph instance
pipeline_graph = create_pipeline_graph()


async def run_pipeline(
    pipeline_id: str,
    run_id: str,
    requirements: str,
    acceptance_criteria: str,
    application_context: str,
    git_ref: str = "main",
    environment: str = "staging",
    triggered_by: str = "manual",
    max_retries: int = 3,
    pipeline_timeout: int = 3600,
    config: Dict[str, Any] = None,
) -> AgenticSTLCState:
    """
    Execute the complete STLC pipeline.
    
    Args:
        pipeline_id: Unique pipeline identifier
        run_id: Unique run identifier
        requirements: Requirements/user stories text
        acceptance_criteria: Acceptance criteria text
        application_context: Application under test context
        git_ref: Git reference (branch/tag/SHA)
        environment: Target environment
        triggered_by: Trigger source
        max_retries: Maximum retries for failed stages
        pipeline_timeout: Pipeline timeout in seconds
        config: Optional LangGraph config
        
    Returns:
        Final pipeline state
    """
    from src.state import create_initial_state
    
    # Create initial state
    initial_state = create_initial_state(
        pipeline_id=pipeline_id,
        run_id=run_id,
        requirements=requirements,
        acceptance_criteria=acceptance_criteria,
        application_context=application_context,
        git_ref=git_ref,
        environment=environment,
        triggered_by=triggered_by,
        max_retries=max_retries,
        pipeline_timeout=pipeline_timeout,
    )
    
    # Execute pipeline
    logger.info(f"Starting pipeline {pipeline_id} run {run_id}")
    
    final_state = None
    async for state in pipeline_graph.astream(initial_state, config=config or {}):
        final_state = state
    
    logger.info(f"Pipeline {pipeline_id} run {run_id} completed with status: {final_state.get('status')}")
    return final_state


def get_graph_visualization() -> str:
    """Get Mermaid diagram of the pipeline graph."""
    return """
graph TD
    A[Initialized] --> B[RAG Retrieval]
    B --> C[Test Authoring<br/>Agent 1: Nemotron]
    C --> D[Script Generation<br/>Agent 2: Nemotron]
    D --> E[Selector Healing<br/>Agent 2b: MCP + Nemotron]
    E --> F[CI/CD Execution<br/>Agent 3: GitHub Actions]
    F --> G[Failure Analysis<br/>Agent 4: Nemotron + Jira]
    G --> H[Completed]
    
    style A fill:#f9f,stroke:#333
    style H fill:#9f9,stroke:#333
    style C fill:#ff9,stroke:#333
    style D fill:#ff9,stroke:#333
    style E fill:#ff9,stroke:#333
    style F fill:#9ff,stroke:#333
    style G fill:#f9f,stroke:#333
"""