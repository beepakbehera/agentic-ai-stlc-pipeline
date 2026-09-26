"""
Stage 3: Agent 2 - Playwright / Robot Script Generator Node.

Uses NVIDIA Nemotron 3 Ultra 550B to generate production-ready
Playwright TypeScript and Robot Framework automation scripts.
"""

import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

import httpx
from pydantic import ValidationError
from langsmith import traceable
from langsmith.wrappers import wrap_openai
from openai import AsyncOpenAI

from src.state import AgenticSTLCState, AutomationScript, PageObject, TestSuite
from config.settings import get_settings
from config.prompt_templates import get_agent2_prompt

logger = logging.getLogger(__name__)
settings = get_settings()


# Mock response for testing without valid API key
MOCK_SCRIPTS = {
    "playwright": {
        "file_path": "tests/generated/login.spec.ts",
        "content": "// Mock Playwright test for login\nimport { test, expect } from '@playwright/test';\n\ntest.describe('Login', () => {\n  test('valid user login', async ({ page }) => {\n    await page.goto('/login');\n    await page.fill('[data-testid=email-input]', 'test@example.com');\n    await page.fill('[data-testid=password-input]', 'password');\n    await page.click('[data-testid=login-button]');\n    await expect(page).toHaveURL('/dashboard');\n  });\n});",
        "page_objects": [
            {"name": "LoginPage", "url_pattern": "/login", "selectors": {"email": "[data-testid=email-input]", "password": "[data-testid=password-input]", "login": "[data-testid=login-button]"}, "methods": ["login"]}
        ]
    },
    "robotframework": {
        "file_path": "tests/generated/login.robot",
        "content": "*** Settings ***\nLibrary    Browser\n\n*** Test Cases ***\nValid Login\n    New Browser    chromium\n    New Page\n    Go To    https://example.com/login\n    Fill    [data-testid=email-input]    test@example.com\n    Fill    [data-testid=password-input]    password\n    Click    [data-testid=login-button]\n    Wait For URL    */dashboard\n    Close Browser",
        "page_objects": [
            {"name": "LoginPage", "url_pattern": "/login", "selectors": {"email": "[data-testid=email-input]", "password": "[data-testid=password-input]", "login": "[data-testid=login-button]"}, "methods": ["login"]}
        ]
    }
}


class Agent2ScriptGenerator:
    """Agent 2: Automation Script Generator using Nemotron 3 Ultra 550B."""
    
    def __init__(self):
        self.api_key = settings.nemotron_api_key.get_secret_value()
        self.base_url = settings.nemotron_base_url.rstrip("/")
        self.model = settings.nemotron_model
        self.temperature = settings.nemotron_temperature
        self.max_tokens = settings.nemotron_max_tokens
        self.use_mock = not self.api_key or self.api_key == "your-nemotron-api-key-here"
        
        if not self.use_mock:
            # Use OpenAI-compatible client wrapped for LangSmith tracing
            self.client = wrap_openai(
                AsyncOpenAI(
                    api_key=self.api_key,
                    base_url=self.base_url,
                    timeout=180.0
                )
            )
        else:
            self.client = None
            logger.info("Agent2 running in MOCK mode - using predefined scripts")
    
    @traceable(name="agent2_generate_scripts")
    async def generate_scripts(self, prompt: str, use_mock_override: bool = None) -> tuple[Dict[str, Any], int]:
        """
        Call Nemotron API to generate automation scripts using wrapped OpenAI client.
        
        Args:
            prompt: Complete prompt for script generation
            use_mock_override: Override the instance's use_mock setting
            
        Returns:
            Tuple of (parsed JSON response with scripts, tokens_used)
        """
        use_mock = use_mock_override if use_mock_override is not None else self.use_mock
        
        if use_mock or self.client is None:
            logger.info("Using MOCK scripts for Agent 2")
            return MOCK_SCRIPTS, 0
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert Test Automation Engineer."},
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
            return MOCK_SCRIPTS, 0


# Global agent instance
agent2 = Agent2ScriptGenerator()


async def agent2_script_gen_node(state: AgenticSTLCState) -> AgenticSTLCState:
    """
    LangGraph node for Script Generation (Agent 2).
    
    Generates Playwright TypeScript and Robot Framework automation scripts
    from structured test cases using Nemotron 3 Ultra 550B.
    """
    logger.info(f"[{state['run_id']}] Starting Stage 3: Script Generation (Agent 2)")
    start_time = datetime.utcnow()
    
    try:
        # Validate test suite exists
        if not state.get("test_suite") or not state["test_suite"].test_cases:
            raise ValueError("No test cases available for script generation")
        
        test_suite: TestSuite = state["test_suite"]
        
        # Serialize test cases for prompt
        test_cases_json = json.dumps({
            "test_cases": [tc.model_dump() for tc in test_suite.test_cases]
        }, indent=2)
        
        # Serialize existing page objects
        page_objects_json = json.dumps({
            "page_objects": [po.model_dump() for po in state.get("page_objects", [])]
        }, indent=2)
        
        # Generate prompt
        prompt = get_agent2_prompt(
            test_cases=test_cases_json,
            application_context=state["application_context"],
            page_objects=page_objects_json,
        )
        state["agent2_prompt"] = prompt
        
        # Call Nemotron API
        # Check if we should use mock mode (either agent's own mock or state mock)
        use_mock = agent2.use_mock or state.get("mock_mode", False)
        response_data, tokens_used = await agent2.generate_scripts(prompt, use_mock_override=use_mock)
        state["agent2_response"] = json.dumps(response_data, indent=2)
        state["agent2_tokens_used"] = tokens_used
        
        # Parse generated scripts
        scripts = []
        page_objects = []
        
        # Handle Playwright scripts
        if "playwright" in response_data:
            pw_data = response_data["playwright"]
            if isinstance(pw_data, dict):
                scripts.append(AutomationScript(
                    language="playwright",
                    file_path=pw_data.get("file_path", "tests/generated.spec.ts"),
                    content=pw_data.get("content", ""),
                    page_objects=[PageObject(**po) for po in pw_data.get("page_objects", [])],
                ))
                page_objects.extend([PageObject(**po) for po in pw_data.get("page_objects", [])])
        
        # Handle Robot Framework scripts
        if "robotframework" in response_data:
            rf_data = response_data["robotframework"]
            if isinstance(rf_data, dict):
                scripts.append(AutomationScript(
                    language="robotframework",
                    file_path=rf_data.get("file_path", "tests/generated.robot"),
                    content=rf_data.get("content", ""),
                    page_objects=[PageObject(**po) for po in rf_data.get("page_objects", [])],
                ))
                page_objects.extend([PageObject(**po) for po in rf_data.get("page_objects", [])])
        
        # Handle direct scripts array
        if "scripts" in response_data:
            for script_data in response_data["scripts"]:
                scripts.append(AutomationScript(**script_data))
        
        state["automation_scripts"] = scripts
        state["page_objects"] = page_objects
        
        # Write scripts to files
        await _write_scripts_to_disk(scripts, state["run_id"])
        
        # Update state
        state["current_stage"] = "script_generation"
        state["updated_at"] = datetime.utcnow()
        state["stages_completed"].append("script_generation")
        state["total_tokens_used"] += tokens_used
        
        duration = (datetime.utcnow() - start_time).total_seconds()
        state["agent2_duration_seconds"] = duration
        state["total_duration_seconds"] += duration
        
        logger.info(f"[{state['run_id']}] Script Generation completed in {duration:.2f}s, generated {len(scripts)} scripts, used {tokens_used} tokens")
        
    except ValidationError as e:
        logger.error(f"[{state['run_id']}] Script validation failed: {e}")
        state["errors"].append({
            "stage": "script_generation",
            "error": f"Validation error: {e}",
            "timestamp": datetime.utcnow().isoformat(),
        })
        state["stages_failed"].append("script_generation")
        state["status"] = "failed"
    except Exception as e:
        logger.error(f"[{state['run_id']}] Script Generation failed: {e}")
        state["errors"].append({
            "stage": "script_generation",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        })
        state["stages_failed"].append("script_generation")
        state["status"] = "failed"
    
    return state


async def _write_scripts_to_disk(scripts: List[AutomationScript], run_id: str) -> None:
    """Write generated scripts to disk."""
    output_dir = Path(f"tests/generated/{run_id}")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    for script in scripts:
        file_path = output_dir / Path(script.file_path).name
        file_path.write_text(script.content, encoding="utf-8")
        logger.info(f"Written script: {file_path}")