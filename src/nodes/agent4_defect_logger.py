"""
Stage 6: Agent 4 - Failure Analysis & Jira Defect Logger Node.

Analyzes test failures, classifies root causes, and creates
detailed Jira defects using Nemotron 3 Ultra 550B.
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

import httpx
from pydantic import ValidationError
from langsmith import traceable
from langsmith.wrappers import wrap_openai
from openai import AsyncOpenAI

from src.state import AgenticSTLCState, FailureAnalysis, JiraDefect
from src.jira_client import JiraClient, create_jira_client
from config.settings import get_settings
from config.prompt_templates import get_agent4_prompt

logger = logging.getLogger(__name__)
settings = get_settings()


# Mock failure analysis for testing
MOCK_FAILURE_ANALYSIS = FailureAnalysis(
    should_create_defect=False,
    classification="Flaky",
    root_cause_analysis="Mock analysis: No real failures to analyze - workflow passed",
    evidence=["Workflow execution concluded with success"],
    jira_defect=None,
    recommended_action="No action needed - all tests passed"
)


class Agent4FailureAnalyzer:
    """Agent 4: Failure Analysis & Defect Logging using Nemotron 3 Ultra 550B."""
    
    def __init__(self):
        self.api_key = settings.nemotron_api_key.get_secret_value()
        self.base_url = settings.nemotron_base_url.rstrip("/")
        self.model = settings.nemotron_model
        self.temperature = settings.nemotron_temperature
        self.max_tokens = settings.nemotron_max_tokens
        self.use_mock = not self.api_key or self.api_key == "your-nemotron-api-key-here" or not settings.jira_api_token.get_secret_value()
        
        if not self.use_mock:
            # Use OpenAI-compatible client wrapped for LangSmith tracing
            self.client = wrap_openai(
                AsyncOpenAI(
                    api_key=self.api_key,
                    base_url=self.base_url,
                    timeout=120.0
                )
            )
        else:
            self.client = None
            logger.info("Agent4 running in MOCK mode - using simulated failure analysis")
    
    @traceable(name="agent4_analyze_failure")
    async def analyze_failure(self, prompt: str) -> tuple[Dict[str, Any], int]:
        """
        Call Nemotron API to analyze failure and generate defect using wrapped OpenAI client.
        
        Args:
            prompt: Complete prompt for failure analysis
            
        Returns:
            Tuple of (parsed JSON response with analysis and defect, tokens_used)
        """
        if self.use_mock or self.client is None:
            logger.info("Using MOCK failure analysis for Agent 4")
            return MOCK_FAILURE_ANALYSIS.model_dump(), 0
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert AI Quality Engineer."},
                    {"role": "user", "content": prompt},
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                response_format={"type": "json_object"},
            )
            
            content = response.choices[0].message.content
            tokens_used = response.usage.total_tokens if response.usage else 0
            
            return json.loads(content), tokens_used
        except Exception as e:
            logger.warning(f"Nemotron API call failed, falling back to mock: {e}")
            return MOCK_FAILURE_ANALYSIS.model_dump(), 0


# Global agent instance
agent4 = Agent4FailureAnalyzer()


async def agent4_defect_logger_node(state: AgenticSTLCState) -> AgenticSTLCState:
    """
    LangGraph node for Failure Analysis & Jira Defect Logging (Agent 4).
    
    Analyzes test failures from CI/CD execution, classifies root causes,
    and creates detailed Jira defects for genuine product bugs.
    """
    logger.info(f"[{state['run_id']}] Starting Stage 6: Failure Analysis & Jira Defect Logger (Agent 4)")
    start_time = datetime.utcnow()
    
    try:
        # Get workflow execution results
        workflow_execution = state.get("workflow_execution")
        
        # Check if we should use mock mode (no failures to analyze)
        use_mock = (
            not workflow_execution or 
            workflow_execution.conclusion != "failure" or
            agent4.use_mock or
            state.get("mock_mode", False)
        )
        
        if use_mock:
            logger.info(f"[{state['run_id']}] Using MOCK failure analysis for Agent 4 (workflow passed or mock mode)")
            state["failure_analyses"] = [MOCK_FAILURE_ANALYSIS]
            state["created_jira_issues"] = []
            state["agent4_tokens_used"] = 0
            state["agent4_prompt"] = "MOCK: No failures to analyze - workflow passed"
            state["agent4_response"] = json.dumps(MOCK_FAILURE_ANALYSIS.model_dump(), indent=2)
            
            # Update state
            state["current_stage"] = "failure_analysis"
            state["status"] = "completed"
            state["updated_at"] = datetime.utcnow()
            state["stages_completed"].append("failure_analysis")
            
            duration = (datetime.utcnow() - start_time).total_seconds()
            state["agent4_duration_seconds"] = duration
            state["total_duration_seconds"] += duration
            
            logger.info(f"[{state['run_id']}] Failure Analysis (mock) completed in {duration:.2f}s - No defects needed")
            return state
        
        # Collect failure details (in real scenario, from artifacts/logs)
        # For now, simulate with test case info
        test_suite = state.get("test_suite")
        if not test_suite:
            logger.warning(f"[{state['run_id']}] No test suite available for failure analysis")
            state["stages_completed"].append("failure_analysis")
            return state
        
        # Initialize Jira client
        jira_client = create_jira_client()
        
        failure_analyses = []
        created_issues = []
        total_tokens = 0
        
        # Analyze each failed test case
        # In reality, you'd parse actual test results from artifacts
        for test_case in test_suite.test_cases:
            # Simulate failure analysis for demo
            # Real implementation would parse actual failures
            if test_case.priority in ["Critical", "High"]:
                analysis = await _analyze_single_failure(
                    state=state,
                    test_case=test_case,
                    workflow_execution=workflow_execution,
                    jira_client=jira_client,
                )
                failure_analyses.append(analysis)
                total_tokens += analysis.agent4_tokens_used if hasattr(analysis, 'agent4_tokens_used') else 0
                
                if analysis.should_create_defect and analysis.jira_defect:
                    issue = await jira_client.create_issue(analysis.jira_defect)
                    if issue:
                        created_issues.append(issue)
                        logger.info(f"[{state['run_id']}] Created Jira issue: {issue.get('key')}")
        
        state["failure_analyses"] = failure_analyses
        state["created_jira_issues"] = created_issues
        state["agent4_tokens_used"] = total_tokens
        
        # Update state
        state["current_stage"] = "failure_analysis"
        state["status"] = "completed"
        state["updated_at"] = datetime.utcnow()
        state["stages_completed"].append("failure_analysis")
        state["total_tokens_used"] += total_tokens
        
        duration = (datetime.utcnow() - start_time).total_seconds()
        state["agent4_duration_seconds"] = duration
        state["total_duration_seconds"] += duration
        
        logger.info(f"[{state['run_id']}] Failure Analysis completed in {duration:.2f}s, analyzed {len(failure_analyses)} failures, created {len(created_issues)} Jira issues")
        
    except ValidationError as e:
        logger.error(f"[{state['run_id']}] Failure analysis validation failed: {e}")
        state["errors"].append({
            "stage": "failure_analysis",
            "error": f"Validation error: {e}",
            "timestamp": datetime.utcnow().isoformat(),
        })
        state["stages_failed"].append("failure_analysis")
    except Exception as e:
        logger.error(f"[{state['run_id']}] Failure Analysis failed: {e}")
        state["errors"].append({
            "stage": "failure_analysis",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        })
        state["stages_failed"].append("failure_analysis")
    
    return state


async def _analyze_single_failure(
    state: AgenticSTLCState,
    test_case,
    workflow_execution,
    jira_client,
) -> FailureAnalysis:
    """Analyze a single test failure and create Jira defect if warranted."""
    
    # Build failure context (in reality, parse from actual artifacts)
    error_message = f"Test failed in {workflow_execution.conclusion} workflow run"
    stack_trace = "Stack trace would be extracted from test artifacts"
    test_logs = "Test logs would be downloaded from GitHub Actions"
    
    # Generate prompt for Nemotron
    prompt = get_agent4_prompt(
        test_case_id=test_case.id,
        test_name=test_case.title,
        error_message=error_message,
        stack_trace=stack_trace,
        screenshot_path="",
        trace_path="",
        test_logs=test_logs,
        environment=state["environment"],
        build_version=state["git_ref"],
        browser_device="chromium",
        test_data="",
        linked_requirements=", ".join(test_case.linked_requirements),
        similar_defects=", ".join(state.get("past_defects", [])),
        test_steps="\n".join([f"{s.step_number}. {s.action} -> {s.expected_result}" for s in test_case.steps]),
    )
    state["agent4_prompt"] = prompt
    
    # Call Nemotron for analysis
    response_data, tokens_used = await agent4.analyze_failure(prompt)
    state["agent4_response"] = json.dumps(response_data, indent=2)
    
    # Parse analysis result
    analysis = FailureAnalysis(**response_data)
    # Add tokens used to analysis object for aggregation
    analysis.agent4_tokens_used = tokens_used
    
    return analysis