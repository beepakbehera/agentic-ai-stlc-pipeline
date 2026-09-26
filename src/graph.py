"""
LangGraph State Machine Compilation for Agentic AI STLC Pipeline.

Compiles the 6-stage pipeline into an executable LangGraph workflow
with enhanced LangSmith tracing, retry logic, and observability.
"""

import asyncio
import logging
import time
from typing import Dict, Any, Literal, Optional, Callable

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langsmith import traceable, Client
from langsmith.run_helpers import tracing_context

from src.state import AgenticSTLCState
from src.nodes.rag_retrieval import rag_retrieval_node
from src.nodes.agent1_test_author import agent1_test_author_node
from src.nodes.agent2_script_gen import agent2_script_gen_node
from src.nodes.agent2b_mcp_heal import agent2b_mcp_heal_node
from src.nodes.agent3_cicd_trigger import agent3_cicd_trigger_node
from src.nodes.agent4_defect_logger import agent4_defect_logger_node
from config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Initialize LangSmith client for manual tracing operations
langsmith_client = Client(
    api_key=settings.langsmith_api_key.get_secret_value() if settings.langsmith_api_key else None,
    api_url=settings.langsmith_endpoint,
) if settings.langsmith_tracing and settings.langsmith_api_key else None


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
        return "end"
    
    return "continue"


def route_after_healing(state: AgenticSTLCState) -> Literal["revise_scripts", "cicd_execution", "end"]:
    """
    Conditional edge after Stage 4 (Selector Healing).
    
    Routes back to Stage 3 (Script Generation) when Agent 2b healed
    locators, so the healed locators are applied to the automation
    scripts and the suite is re-executed. Proceeds to Stage 5 (CI/CD)
    when there is nothing to apply or the loop budget is exhausted.
    
    Args:
        state: Current pipeline state
        
    Returns:
        "revise_scripts" to loop back to script_generation,
        "cicd_execution" to continue the normal flow, or
        "end" to terminate on failure
    """
    if state["status"] == "failed":
        logger.info(f"[{state['run_id']}] Pipeline failed at selector healing, ending")
        return "end"
    
    healing_pending = state.get("healing_pending", False)
    rounds = state.get("healing_rounds", 0)
    max_rounds = state.get("max_healing_rounds", 3)
    
    if healing_pending and rounds < max_rounds:
        logger.info(
            f"[{state['run_id']}] Healing loop active: {rounds}/{max_rounds} rounds used, "
            f"routing back to script_generation to apply healed locators"
        )
        return "revise_scripts"
    
    if healing_pending and rounds >= max_rounds:
        logger.warning(
            f"[{state['run_id']}] Healing loop budget exhausted ({rounds}/{max_rounds} rounds); "
            f"proceeding to cicd_execution with current scripts"
        )
    
    return "cicd_execution"


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


def create_retryable_node(
    node_func: Callable,
    node_name: str,
    max_retries: int = 3,
    retry_delay: float = 1.0,
) -> Callable:
    """
    Wrap a node function with retry logic and enhanced tracing.
    
    Args:
        node_func: The original node function
        node_name: Name of the node for tracing
        max_retries: Maximum number of retry attempts
        retry_delay: Base delay between retries (seconds)
        
    Returns:
        Wrapped node function with retry logic
    """
    @traceable(name=f"{node_name}_with_retry", metadata={"node_name": node_name, "max_retries": max_retries})
    async def wrapper(state: AgenticSTLCState) -> AgenticSTLCState:
        last_error = None
        
        for attempt in range(max_retries + 1):
            try:
                # Add attempt metadata to state
                state["_retry_attempt"] = attempt
                state["_retry_max"] = max_retries
                
                if attempt > 0:
                    logger.warning(f"[{state['run_id']}] Retrying {node_name} (attempt {attempt}/{max_retries})")
                    # Exponential backoff
                    await asyncio.sleep(retry_delay * (2 ** (attempt - 1)))
                
                result = await node_func(state)
                
                # Check if node succeeded
                if result.get("status") != "failed" or node_name not in result.get("stages_failed", []):
                    if attempt > 0:
                        logger.info(f"[{state['run_id']}] {node_name} succeeded on retry attempt {attempt}")
                    return result
                    
            except Exception as e:
                last_error = e
                logger.error(f"[{state['run_id']}] {node_name} failed on attempt {attempt + 1}: {e}")
                
                # Add error to state for tracing
                state["errors"].append({
                    "stage": node_name,
                    "error": f"Attempt {attempt + 1} failed: {str(e)}",
                    "timestamp": time.time(),
                    "retry_attempt": attempt,
                })
                
                if attempt == max_retries:
                    logger.error(f"[{state['run_id']}] {node_name} failed after {max_retries + 1} attempts")
                    state["status"] = "failed"
                    state["stages_failed"].append(node_name)
                    # Re-raise to be caught by LangGraph error handling
                    raise
        
        # This shouldn't be reached, but just in case
        raise last_error or Exception(f"{node_name} failed after retries")
    
    return wrapper


def create_pipeline_graph(
    enable_retry: bool = True,
    max_retries: int = 3,
) -> StateGraph:
    """
    Create and compile the LangGraph state machine for the STLC Pipeline.
    
    Args:
        enable_retry: Whether to enable retry logic on nodes
        max_retries: Maximum retries per node
        
    Returns:
        Compiled StateGraph ready for execution
    """
    # Create graph with state schema
    workflow = StateGraph(AgenticSTLCState)
    
    # Wrap nodes with retry logic if enabled
    nodes = {
        "rag_retrieval": rag_retrieval_node,
        "test_authoring": agent1_test_author_node,
        "script_generation": agent2_script_gen_node,
        "selector_healing": agent2b_mcp_heal_node,
        "cicd_execution": agent3_cicd_trigger_node,
        "failure_analysis": agent4_defect_logger_node,
    }
    
    if enable_retry:
        wrapped_nodes = {
            name: create_retryable_node(func, name, max_retries)
            for name, func in nodes.items()
        }
    else:
        wrapped_nodes = nodes
    
    # Add nodes for each stage
    for name, func in wrapped_nodes.items():
        workflow.add_node(name, func)
    
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
        route_after_healing,
        {
            "revise_scripts": "script_generation",
            "cicd_execution": "cicd_execution",
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
    
    # Compile with memory checkpointing for debugging and resume capability
    checkpointer = MemorySaver()
    app = workflow.compile(
        checkpointer=checkpointer,
        interrupt_before=[],  # Can add nodes to pause before for debugging
        interrupt_after=[],   # Can add nodes to pause after for inspection
    )
    
    logger.info("LangGraph pipeline compiled successfully with tracing and retry logic")
    return app


# Compiled graph instance with default settings
pipeline_graph = create_pipeline_graph()


@traceable(
    name="run_pipeline",
    metadata={
        "pipeline": "agentic-ai-stlc",
        "version": "1.0.0",
    }
)
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
    mock_mode: bool = False,
    config: Optional[Dict[str, Any]] = None,
    enable_retry: bool = True,
) -> AgenticSTLCState:
    """
    Execute the complete STLC pipeline with LangSmith tracing.
    
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
        mock_mode: Run in mock mode (skip real API calls)
        config: Optional LangGraph config (must include configurable.thread_id for checkpointer)
        enable_retry: Enable retry logic on nodes
        
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
        mock_mode=mock_mode,
    )
    
    # Ensure config has thread_id for checkpointer
    run_config = config or {}
    if "configurable" not in run_config:
        run_config["configurable"] = {}
    if "thread_id" not in run_config["configurable"]:
        run_config["configurable"]["thread_id"] = run_id
    
    # Add tracing metadata
    run_config["metadata"] = {
        **run_config.get("metadata", {}),
        "pipeline_id": pipeline_id,
        "run_id": run_id,
        "environment": environment,
        "git_ref": git_ref,
        "mock_mode": mock_mode,
    }
    
    # Create pipeline graph with retry settings
    graph = create_pipeline_graph(enable_retry=enable_retry, max_retries=max_retries)
    
    # Execute pipeline
    logger.info(f"Starting pipeline {pipeline_id} run {run_id}")
    start_time = time.time()
    
    final_state = None
    try:
        async for state_update in graph.astream(initial_state, config=run_config):
            # astream yields {node_name: state_after_node}
            # We want the latest state
            for node_name, state in state_update.items():
                final_state = state
                # Log stage transitions for tracing
                logger.debug(f"[{run_id}] Completed stage: {node_name}, status: {state.get('status')}")
        
        duration = time.time() - start_time
        logger.info(f"Pipeline {pipeline_id} run {run_id} completed in {duration:.2f}s with status: {final_state.get('status') if final_state else 'None'}")
        
        # Add final metadata
        if final_state:
            final_state["total_duration_seconds"] = duration
            
    except Exception as e:
        duration = time.time() - start_time
        logger.exception(f"Pipeline {pipeline_id} run {run_id} failed after {duration:.2f}s: {e}")
        # Create error state for tracing
        if final_state is None:
            final_state = initial_state
        final_state["status"] = "failed"
        final_state["errors"].append({
            "stage": "pipeline",
            "error": f"Pipeline execution failed: {str(e)}",
            "timestamp": time.time(),
        })
        final_state["total_duration_seconds"] = duration
        raise
    
    return final_state


async def run_pipeline_streaming(
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
    mock_mode: bool = False,
    config: Optional[Dict[str, Any]] = None,
) -> Any:
    """
    Execute pipeline with streaming for real-time observability.
    
    Yields:
        State updates after each node completion for real-time monitoring
    """
    from src.state import create_initial_state
    
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
        mock_mode=mock_mode,
    )
    
    run_config = config or {}
    if "configurable" not in run_config:
        run_config["configurable"] = {}
    if "thread_id" not in run_config["configurable"]:
        run_config["configurable"]["thread_id"] = run_id
    
    graph = create_pipeline_graph(enable_retry=True, max_retries=max_retries)
    
    async for state_update in graph.astream(initial_state, config=run_config):
        for node_name, state in state_update.items():
            yield {
                "node": node_name,
                "state": state,
                "timestamp": time.time(),
            }


def get_graph_visualization() -> str:
    """Get Mermaid diagram of the pipeline graph."""
    return """
graph TD
    A[Initialized] --> B[RAG Retrieval]
    B --> C[Test Authoring<br/>Agent 1: Nemotron]
    C --> D[Script Generation<br/>Agent 2: Nemotron]
    D --> E[Selector Healing<br/>Agent 2b: MCP + Nemotron]
    E -->|healed locators - loop back| D
    E -->|no healing / budget exhausted| F[CI/CD Execution<br/>Agent 3: GitHub Actions]
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


def get_langsmith_dashboard_url(run_id: Optional[str] = None) -> str:
    """Get LangSmith dashboard URL for the project or specific run."""
    base_url = settings.langsmith_endpoint.replace("/api", "").rstrip("/")
    if run_id:
        return f"{base_url}/o/default/projects/p/{settings.langsmith_project}/r/{run_id}"
    return f"{base_url}/o/default/projects/p/{settings.langsmith_project}"