"""
State schema for the Agentic AI STLC Pipeline.

Defines the TypedDict structure that flows through the LangGraph state machine.
"""

from typing import TypedDict, List, Dict, Any, Optional, Literal
from datetime import datetime
from pydantic import BaseModel, Field


# =============================================================================
# Core Data Models
# =============================================================================

class TestCaseStep(BaseModel):
    """Individual test step."""
    step_number: int
    action: str
    test_data: str = ""
    expected_result: str = ""


class TestCase(BaseModel):
    """Structured test case model."""
    id: str
    title: str
    description: str = ""
    priority: Literal["Critical", "High", "Medium", "Low"] = "Medium"
    type: Literal["Functional", "Non-Functional", "Regression", "Smoke", "Integration", "API", "UI", "Security", "Performance"] = "Functional"
    preconditions: List[str] = Field(default_factory=list)
    steps: List[TestCaseStep] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    linked_requirements: List[str] = Field(default_factory=list)
    automation_feasibility: Literal["High", "Medium", "Low", "Manual Only"] = "Medium"


class TestSuite(BaseModel):
    """Collection of test cases with summary."""
    test_cases: List[TestCase] = Field(default_factory=list)
    summary: Dict[str, Any] = Field(default_factory=dict)


class PageObject(BaseModel):
    """Page Object Model representation."""
    name: str
    url_pattern: str
    selectors: Dict[str, str] = Field(default_factory=dict)
    methods: List[str] = Field(default_factory=list)


class AutomationScript(BaseModel):
    """Generated automation script."""
    language: Literal["playwright", "robotframework"]
    file_path: str
    content: str
    page_objects: List[PageObject] = Field(default_factory=list)


class SelectorHealingResult(BaseModel):
    """Result of selector self-healing."""
    healed_selector: str
    selector_strategy: Literal["data-testid", "role", "text", "label", "css", "xpath"]
    confidence: float
    alternatives: List[Dict[str, Any]] = Field(default_factory=list)
    patch: Optional[Dict[str, Any]] = None
    requires_manual_review: bool = False


class WorkflowExecution(BaseModel):
    """GitHub Actions workflow execution result."""
    workflow_run_id: int
    status: Literal["queued", "in_progress", "completed"]
    conclusion: Optional[Literal["success", "failure", "neutral", "cancelled", "skipped", "timed_out", "action_required"]] = None
    duration_seconds: int = 0
    test_results: Dict[str, int] = Field(default_factory=lambda: {"total": 0, "passed": 0, "failed": 0, "skipped": 0, "flaky": 0})
    artifacts: List[str] = Field(default_factory=list)
    logs_url: str = ""
    retry_triggered: bool = False


class JiraDefect(BaseModel):
    """Jira defect model."""
    summary: str
    description: str
    priority: Literal["Highest", "High", "Medium", "Low", "Lowest"] = "Medium"
    severity: Literal["Critical", "Major", "Minor", "Cosmetic"] = "Major"
    labels: List[str] = Field(default_factory=list)
    components: List[str] = Field(default_factory=list)
    steps_to_reproduce: List[str] = Field(default_factory=list)
    expected_behavior: str = ""
    actual_behavior: str = ""
    attachments: List[str] = Field(default_factory=list)
    linked_test_cases: List[str] = Field(default_factory=list)


class FailureAnalysis(BaseModel):
    """Failure analysis result."""
    should_create_defect: bool
    classification: Literal["Product Bug", "Test Script Issue", "Environment", "Flaky", "Infrastructure"]
    root_cause_analysis: str
    evidence: List[str] = Field(default_factory=list)
    jira_defect: Optional[JiraDefect] = None
    recommended_action: str = ""


class RAGDocument(BaseModel):
    """RAG retrieved document."""
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    score: float = 0.0


# =============================================================================
# Main State TypedDict
# =============================================================================

class AgenticSTLCState(TypedDict):
    """
    Complete state for the Agentic AI STLC Pipeline.
    
    This state flows through all 6 stages of the LangGraph workflow:
    1. RAG Retrieval & Ingestion
    2. Test Case Authoring (Agent 1)
    3. Script Generation (Agent 2)
    4. MCP Selector Self-Healing (Agent 2b)
    5. CI/CD Trigger & Monitoring (Agent 3)
    6. Failure Analysis & Jira Defect Logging (Agent 4)
    """
    
    # ---- Pipeline Metadata ----
    pipeline_id: str
    run_id: str
    started_at: datetime
    updated_at: datetime
    current_stage: Literal[
        "initialized",
        "rag_retrieval",
        "test_authoring",
        "script_generation",
        "selector_healing",
        "cicd_execution",
        "failure_analysis",
        "completed",
        "failed"
    ]
    status: Literal["running", "completed", "failed", "cancelled"]
    
    # ---- Input Context ----
    requirements: str
    acceptance_criteria: str
    application_context: str
    git_ref: str
    environment: str
    triggered_by: str
    
    # ---- Stage 1: RAG Retrieval ----
    rag_documents: List[RAGDocument]
    rag_query: str
    similar_features: List[str]
    past_defects: List[str]
    domain_knowledge: List[str]
    
    # ---- Stage 2: Test Authoring (Agent 1) ----
    test_suite: Optional[TestSuite]
    agent1_prompt: str
    agent1_response: str
    agent1_tokens_used: int
    agent1_duration_seconds: float
    
    # ---- Stage 3: Script Generation (Agent 2) ----
    automation_scripts: List[AutomationScript]
    page_objects: List[PageObject]
    agent2_prompt: str
    agent2_response: str
    agent2_tokens_used: int
    agent2_duration_seconds: float
    
    # ---- Stage 4: Selector Healing (Agent 2b) ----
    healing_results: List[SelectorHealingResult]
    failed_selectors: List[Dict[str, Any]]
    mcp_responses: List[Dict[str, Any]]
    agent2b_prompt: str
    agent2b_response: str
    agent2b_tokens_used: int
    agent2b_duration_seconds: float
    
    # ---- Stage 5: CI/CD Execution (Agent 3) ----
    workflow_execution: Optional[WorkflowExecution]
    workflow_dispatch_payload: Dict[str, Any]
    agent3_prompt: str
    agent3_response: str
    agent3_tokens_used: int
    agent3_duration_seconds: float
    
    # ---- Stage 6: Failure Analysis (Agent 4) ----
    failure_analyses: List[FailureAnalysis]
    created_jira_issues: List[Dict[str, Any]]
    agent4_prompt: str
    agent4_response: str
    agent4_tokens_used: int
    agent4_duration_seconds: float
    
    # ---- Aggregated Metrics ----
    total_tokens_used: int
    total_duration_seconds: float
    stages_completed: List[str]
    stages_failed: List[str]
    errors: List[Dict[str, Any]]
    
    # ---- Configuration ----
    max_retries: int
    pipeline_timeout: int
    mock_mode: bool


# =============================================================================
# Initial State Factory
# =============================================================================

def create_initial_state(
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
) -> AgenticSTLCState:
    """Create initial pipeline state."""
    now = datetime.utcnow()
    return AgenticSTLCState(
        pipeline_id=pipeline_id,
        run_id=run_id,
        started_at=now,
        updated_at=now,
        current_stage="initialized",
        status="running",
        requirements=requirements,
        acceptance_criteria=acceptance_criteria,
        application_context=application_context,
        git_ref=git_ref,
        environment=environment,
        triggered_by=triggered_by,
        rag_documents=[],
        rag_query="",
        similar_features=[],
        past_defects=[],
        domain_knowledge=[],
        test_suite=None,
        agent1_prompt="",
        agent1_response="",
        agent1_tokens_used=0,
        agent1_duration_seconds=0.0,
        automation_scripts=[],
        page_objects=[],
        agent2_prompt="",
        agent2_response="",
        agent2_tokens_used=0,
        agent2_duration_seconds=0.0,
        healing_results=[],
        failed_selectors=[],
        mcp_responses=[],
        agent2b_prompt="",
        agent2b_response="",
        agent2b_tokens_used=0,
        agent2b_duration_seconds=0.0,
        workflow_execution=None,
        workflow_dispatch_payload={},
        agent3_prompt="",
        agent3_response="",
        agent3_tokens_used=0,
        agent3_duration_seconds=0.0,
        failure_analyses=[],
        created_jira_issues=[],
        agent4_prompt="",
        agent4_response="",
        agent4_tokens_used=0,
        agent4_duration_seconds=0.0,
        total_tokens_used=0,
        total_duration_seconds=0.0,
        stages_completed=[],
        stages_failed=[],
        errors=[],
        max_retries=max_retries,
        pipeline_timeout=pipeline_timeout,
        mock_mode=mock_mode,
    )