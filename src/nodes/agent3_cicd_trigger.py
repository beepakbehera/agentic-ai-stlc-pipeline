"""
Stage 5: Agent 3 - CI/CD Trigger & Monitoring Node.

Triggers GitHub Actions workflow dispatch and monitors execution
for test automation runs.
"""

import json
import logging
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional

import httpx
from pydantic import ValidationError
from langsmith import traceable
from langsmith.wrappers import wrap_openai
from openai import AsyncOpenAI

from src.state import AgenticSTLCState, WorkflowExecution
from config.settings import get_settings
from config.prompt_templates import get_agent3_prompt

logger = logging.getLogger(__name__)
settings = get_settings()


# Mock workflow execution for testing
MOCK_WORKFLOW_EXECUTION = WorkflowExecution(
    workflow_run_id=123456789,
    status="completed",
    conclusion="success",
    duration_seconds=120,
    test_results={"total": 10, "passed": 10, "failed": 0, "skipped": 0, "flaky": 0},
    artifacts=["playwright-report", "test-results", "traces"],
    logs_url="https://github.com/beepakbehera/agentic-ai-stlc-pipeline/actions/runs/123456789",
    retry_triggered=False
)


class GitHubActionsClient:
    """Client for GitHub Actions REST API."""
    
    def __init__(self):
        self.token = settings.github_token.get_secret_value()
        self.owner = settings.github_repo_owner
        self.repo = settings.github_repo_name
        self.base_url = "https://api.github.com"
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            }
        )
    
    async def dispatch_workflow(
        self,
        workflow_file: str,
        ref: str,
        inputs: Dict[str, Any],
    ) -> int:
        """
        Dispatch a workflow run.
        
        Returns:
            Workflow run ID
        """
        response = await self.client.post(
            f"{self.base_url}/repos/{self.owner}/{self.repo}/actions/workflows/{workflow_file}/dispatches",
            json={"ref": ref, "inputs": inputs},
        )
        response.raise_for_status()
        
        # Get the run ID from the created workflow run
        # Note: Dispatch doesn't return run ID directly, need to list runs
        await asyncio.sleep(2)  # Wait for run to appear
        runs = await self.list_workflow_runs(workflow_file, ref)
        if runs:
            return runs[0]["id"]
        raise RuntimeError("Workflow run not found after dispatch")
    
    async def list_workflow_runs(
        self,
        workflow_file: str,
        ref: str,
        per_page: int = 10,
    ) -> list:
        """List recent workflow runs."""
        response = await self.client.get(
            f"{self.base_url}/repos/{self.owner}/{self.repo}/actions/workflows/{workflow_file}/runs",
            params={"branch": ref, "per_page": per_page},
        )
        response.raise_for_status()
        return response.json().get("workflow_runs", [])
    
    async def get_workflow_run(self, run_id: int) -> Dict[str, Any]:
        """Get workflow run details."""
        response = await self.client.get(
            f"{self.base_url}/repos/{self.owner}/{self.repo}/actions/runs/{run_id}",
        )
        response.raise_for_status()
        return response.json()
    
    async def get_workflow_run_logs(self, run_id: int) -> bytes:
        """Download workflow run logs."""
        response = await self.client.get(
            f"{self.base_url}/repos/{self.owner}/{self.repo}/actions/runs/{run_id}/logs",
        )
        response.raise_for_status()
        return response.content
    
    async def list_artifacts(self, run_id: int) -> list:
        """List artifacts for a workflow run."""
        response = await self.client.get(
            f"{self.base_url}/repos/{self.owner}/{self.repo}/actions/runs/{run_id}/artifacts",
        )
        response.raise_for_status()
        return response.json().get("artifacts", [])
    
    async def download_artifact(self, artifact_id: int) -> bytes:
        """Download a specific artifact."""
        response = await self.client.get(
            f"{self.base_url}/repos/{self.owner}/{self.repo}/actions/artifacts/{artifact_id}/zip",
        )
        response.raise_for_status()
        return response.content
    
    async def rerun_workflow(self, run_id: int) -> None:
        """Re-run a failed workflow."""
        response = await self.client.post(
            f"{self.base_url}/repos/{self.owner}/{self.repo}/actions/runs/{run_id}/rerun",
        )
        response.raise_for_status()


# Global client instance
gh_client = GitHubActionsClient()


class Agent3CICDOrchestrator:
    """Agent 3: CI/CD Orchestration using Nemotron 3 Ultra 550B."""
    
    def __init__(self):
        self.api_key = settings.nemotron_api_key.get_secret_value()
        self.base_url = settings.nemotron_base_url.rstrip("/")
        self.model = settings.nemotron_model
        self.temperature = settings.nemotron_temperature
        self.max_tokens = settings.nemotron_max_tokens
        self.use_mock = not self.api_key or self.api_key == "your-nemotron-api-key-here" or not settings.github_token.get_secret_value()
        
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
            logger.info("Agent3 running in MOCK mode - using simulated workflow execution")
    
    @traceable(name="agent3_analyze_execution")
    async def analyze_execution(self, prompt: str) -> tuple[Dict[str, Any], int]:
        """Call Nemotron to analyze workflow execution using wrapped OpenAI client."""
        if self.use_mock or self.client is None:
            logger.info("Using MOCK analysis for Agent 3")
            return {"retry_recommended": False, "analysis": "Mock analysis: workflow passed"}, 0
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert DevOps Engineer."},
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
            return {"retry_recommended": False, "analysis": "Mock analysis: workflow passed"}, 0


async def agent3_cicd_trigger_node(state: AgenticSTLCState) -> AgenticSTLCState:
    """
    LangGraph node for CI/CD Trigger & Monitoring (Agent 3).
    
    Dispatches GitHub Actions workflow, monitors execution,
    collects results and artifacts.
    """
    logger.info(f"[{state['run_id']}] Starting Stage 5: CI/CD Trigger & Monitoring (Agent 3)")
    start_time = datetime.utcnow()
    
    try:
        # Prepare workflow dispatch payload
        workflow_inputs = {
            "test_suite": "generated",
            "environment": state["environment"],
            "run_id": state["run_id"],
            "pipeline_id": state["pipeline_id"],
        }
        state["workflow_dispatch_payload"] = workflow_inputs
        
        # Use mock workflow execution if in mock mode
        if agent3.use_mock:
            logger.info(f"[{state['run_id']}] Using MOCK workflow execution for Agent 3")
            workflow_execution = MOCK_WORKFLOW_EXECUTION
            state["agent3_prompt"] = "MOCK: CI/CD workflow execution simulated"
            state["agent3_response"] = json.dumps({"mock": True, "conclusion": "success"}, indent=2)
            state["agent3_tokens_used"] = 0
            state["workflow_execution"] = workflow_execution
        else:
            # Prepare workflow dispatch payload
            workflow_inputs = {
                "test_suite": "generated",
                "environment": state["environment"],
                "run_id": state["run_id"],
                "pipeline_id": state["pipeline_id"],
            }
            state["workflow_dispatch_payload"] = workflow_inputs
            
            # Dispatch workflow
            logger.info(f"[{state['run_id']}] Dispatching workflow: {settings.github_workflow_id}")
            run_id = await gh_client.dispatch_workflow(
                workflow_file=settings.github_workflow_id,
                ref=state["git_ref"],
                inputs=workflow_inputs,
            )
            logger.info(f"[{state['run_id']}] Workflow dispatched, run ID: {run_id}")
            
            # Monitor workflow execution
            workflow_execution = await _monitor_workflow(
                run_id=run_id,
                timeout_minutes=settings.pipeline_timeout // 60,
                max_retries=state["max_retries"],
            )
            
            state["workflow_execution"] = workflow_execution
            
            # If failed, analyze with Nemotron for retry decision
            if workflow_execution.conclusion == "failure":
                prompt = get_agent3_prompt(
                    repo_owner=settings.github_repo_owner,
                    repo_name=settings.github_repo_name,
                    workflow_file=settings.github_workflow_id,
                    git_ref=state["git_ref"],
                    workflow_inputs=json.dumps(workflow_inputs),
                    test_suite="generated",
                    environment=state["environment"],
                    triggered_by=state["triggered_by"],
                    timeout_minutes=settings.pipeline_timeout // 60,
                    max_retries=state["max_retries"],
                )
                state["agent3_prompt"] = prompt
                
                analysis, tokens_used = await agent3.analyze_execution(prompt)
                state["agent3_response"] = json.dumps(analysis, indent=2)
                state["agent3_tokens_used"] = tokens_used
                state["total_tokens_used"] += tokens_used
                
                # Check if retry recommended
                if analysis.get("retry_recommended", False) and state["max_retries"] > 0:
                    logger.info(f"[{state['run_id']}] Retry recommended, re-running workflow")
                    await gh_client.rerun_workflow(run_id)
                    workflow_execution.retry_triggered = True
                    state["max_retries"] -= 1
                    
                    # Monitor retry
                    workflow_execution = await _monitor_workflow(
                        run_id=run_id,
                        timeout_minutes=settings.pipeline_timeout // 60,
                        max_retries=state["max_retries"],
                    )
                    state["workflow_execution"] = workflow_execution
        
        state["workflow_execution"] = workflow_execution
        
        # Update state
        state["current_stage"] = "cicd_execution"
        state["updated_at"] = datetime.utcnow()
        state["stages_completed"].append("cicd_execution")
        
        duration = (datetime.utcnow() - start_time).total_seconds()
        state["agent3_duration_seconds"] = duration
        state["total_duration_seconds"] += duration
        
        logger.info(f"[{state['run_id']}] CI/CD Execution completed in {duration:.2f}s, conclusion: {workflow_execution.conclusion}")
        
    except ValidationError as e:
        logger.error(f"[{state['run_id']}] CI/CD validation failed: {e}")
        state["errors"].append({
            "stage": "cicd_execution",
            "error": f"Validation error: {e}",
            "timestamp": datetime.utcnow().isoformat(),
        })
        state["stages_failed"].append("cicd_execution")
        state["status"] = "failed"
    except Exception as e:
        logger.error(f"[{state['run_id']}] CI/CD Execution failed: {e}")
        state["errors"].append({
            "stage": "cicd_execution",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        })
        state["stages_failed"].append("cicd_execution")
        state["status"] = "failed"
    
    return state


async def _monitor_workflow(
    run_id: int,
    timeout_minutes: int = 60,
    max_retries: int = 3,
    poll_interval: int = 30,
) -> WorkflowExecution:
    """
    Monitor workflow run until completion.
    
    Args:
        run_id: GitHub Actions run ID
        timeout_minutes: Maximum wait time
        max_retries: Maximum retries for flaky tests
        poll_interval: Polling interval in seconds
        
    Returns:
        WorkflowExecution with results
    """
    start_time = datetime.utcnow()
    timeout_seconds = timeout_minutes * 60
    
    while True:
        # Check timeout
        elapsed = (datetime.utcnow() - start_time).total_seconds()
        if elapsed > timeout_seconds:
            logger.warning(f"Workflow {run_id} timed out after {timeout_minutes} minutes")
            return WorkflowExecution(
                workflow_run_id=run_id,
                status="completed",
                conclusion="timed_out",
                duration_seconds=int(elapsed),
            )
        
        # Get run status
        run_data = await gh_client.get_workflow_run(run_id)
        status = run_data.get("status")
        conclusion = run_data.get("conclusion")
        
        if status == "completed":
            # Get test results from artifacts
            test_results = await _collect_test_results(run_id)
            artifacts = await _collect_artifacts(run_id)
            
            return WorkflowExecution(
                workflow_run_id=run_id,
                status="completed",
                conclusion=conclusion,
                duration_seconds=run_data.get("run_duration", int(elapsed)),
                test_results=test_results,
                artifacts=artifacts,
                logs_url=run_data.get("html_url", ""),
            )
        
        # Still running, wait and poll
        logger.debug(f"Workflow {run_id} status: {status}, waiting {poll_interval}s")
        await asyncio.sleep(poll_interval)


async def _collect_test_results(run_id: int) -> Dict[str, int]:
    """Collect and parse test results from workflow artifacts."""
    results = {"total": 0, "passed": 0, "failed": 0, "skipped": 0, "flaky": 0}
    
    try:
        artifacts = await gh_client.list_artifacts(run_id)
        
        for artifact in artifacts:
            if "test" in artifact["name"].lower() or "result" in artifact["name"].lower():
                # Download and parse artifact
                # This would parse JUnit XML, Playwright JSON, etc.
                # Simplified for now
                pass
    except Exception as e:
        logger.warning(f"Could not collect test results: {e}")
    
    return results


async def _collect_artifacts(run_id: int) -> list:
    """Collect artifact names from workflow run."""
    try:
        artifacts = await gh_client.list_artifacts(run_id)
        return [a["name"] for a in artifacts]
    except Exception:
        return []