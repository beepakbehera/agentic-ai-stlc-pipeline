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

from src.state import AgenticSTLCState, AutomationScript, PageObject, TestSuite, SelectorHealingResult
from src.nodes.agent2b_mcp_heal import KNOWN_SELECTOR_HEALINGS
from config.settings import get_settings
from config.prompt_templates import get_agent2_prompt

logger = logging.getLogger(__name__)
settings = get_settings()


# Mock response for testing without valid API key
MOCK_SCRIPTS = {
    "playwright": {
        "file_path": "tests/generated/login.spec.ts",
        "content": (
            "// Mock Playwright test for login (saucedemo)\n"
            "import { test, expect } from '@playwright/test';\n\n"
            "test.describe('Login', () => {\n"
            "  test('valid user login', async ({ page }) => {\n"
            "    await page.goto('/');\n"
            "    await page.fill('#user-name', 'standard_user');\n"
            "    await page.fill('#password', 'secret_sauce');\n"
            "    await page.click('#login-button');\n"
            "    await expect(page).toHaveURL(/inventory/);\n"
            "  });\n"
            "});"
        ),
        "page_objects": [
            {"name": "LoginPage", "url_pattern": "/", "selectors": {"username": "#user-name", "password": "#password", "login": "#login-button"}, "methods": ["login"]}
        ]
    },
    "robotframework": {
        "file_path": "tests/generated/login.robot",
        "content": (
            "*** Settings ***\n"
            "Library    Browser\n\n"
            "*** Test Cases ***\n"
            "Valid Login\n"
            "    New Browser    chromium    headless=True\n"
            "    New Page\n"
            "    Go To    https://www.saucedemo.com/\n"
            "    Fill Text    css=#user-name    standard_user\n"
            "    Fill Text    css=#password    secret_sauce\n"
            "    Click    css=#login-button\n"
            "    Wait For Elements State    css=.inventory_list    visible    timeout=30s\n"
            "    Close Browser"
        ),
        "page_objects": [
            {"name": "LoginPage", "url_pattern": "/", "selectors": {"username": "#user-name", "password": "#password", "login": "#login-button"}, "methods": ["login"]}
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
                    timeout=300.0
                )
            )
        else:
            self.client = None
            logger.info("Agent2 running in MOCK mode - using predefined scripts")
    
    @traceable(
        name="agent2_generate_scripts",
        metadata={
            "agent": "agent2_script_generator",
            "model": "nemotron-3-ultra",
            "stage": "script_generation",
        }
    )
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
            
            try:
                return json.loads(content), tokens_used
            except json.JSONDecodeError:
                return json.loads(content, strict=False), tokens_used
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
        
        # -----------------------------------------------------------------
        # Self-healing feedback loop: on loop-back passes (Stage 4 -> Stage 3),
        # apply the healed locators to the previously generated scripts and
        # instruct Agent 2 to re-emit scripts using the healed locators.
        # -----------------------------------------------------------------
        healing_rounds = state.get("healing_rounds", 0)
        healing_results = state.get("healing_results", [])
        is_healing_pass = healing_rounds > 0 and bool(healing_results)
        
        if is_healing_pass:
            logger.info(
                f"[{state['run_id']}] Healing pass {healing_rounds}: applying "
                f"{len(healing_results)} healed locator(s) to scripts"
            )
            # Patch stored scripts in place so they always reflect healed locators,
            # even if the LLM fails to apply every replacement.
            scripts = list(state.get("automation_scripts", []))
            scripts = _apply_healed_locators(scripts, healing_results)
            state["automation_scripts"] = scripts
            
            # Record this loop iteration for tracing/reporting
            state["healing_history"].append({
                "round": healing_rounds,
                "locators_healed": len(healing_results),
                "scripts_patched": len(scripts),
                "timestamp": datetime.utcnow().isoformat(),
            })
            
            # Add healed locator mapping to the prompt so Agent 2 re-emits
            # scripts that consistently use the healed locators.
            healed_map = {
                h.healed_selector: h.selector_strategy
                for h in healing_results
            }
            page_objects_json = json.dumps({
                "page_objects": [po.model_dump() for po in state.get("page_objects", [])],
                "healed_locators_to_apply": {
                    "instruction": (
                        "The following locators previously failed. Use these healed "
                        "locators instead of the failed ones when re-generating scripts."
                    ),
                    "healed_locators": [
                        {
                            "strategy": h.selector_strategy,
                            "healed_selector": h.healed_selector,
                            "confidence": h.confidence,
                        }
                        for h in healing_results
                    ],
                },
            }, indent=2)
            _ = healed_map  # kept for readability; mapping expressed inline above
        
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
            elif isinstance(pw_data, str) and pw_data.strip():
                # LLM returned the raw script content as a string
                scripts.append(AutomationScript(
                    language="playwright",
                    file_path="tests/generated/login.spec.ts",
                    content=pw_data,
                    page_objects=[],
                ))
        
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
            elif isinstance(rf_data, str) and rf_data.strip():
                # LLM returned the raw script content as a string
                scripts.append(AutomationScript(
                    language="robotframework",
                    file_path="tests/generated/login.robot",
                    content=rf_data,
                    page_objects=[],
                ))
        
        # Handle direct scripts array
        if "scripts" in response_data:
            for script_data in response_data["scripts"]:
                scripts.append(AutomationScript(**script_data))
        
        # On healing passes, guarantee the healed locators land in the final
        # scripts even if the LLM re-emission missed some replacements.
        if is_healing_pass:
            scripts = _apply_healed_locators(scripts, healing_results)
        
        # Post-generation normalization: replace locators known to be broken
        # on the target app (learned from past runs / MCP healing server) so
        # freshly generated scripts are executable on first run.
        scripts = [_normalize_selectors(sc) for sc in scripts]
        
        state["automation_scripts"] = scripts
        state["page_objects"] = page_objects
        
        # Write scripts to files (initial and healing passes both persist
        # the latest script content for execution)
        await _write_scripts_to_disk(scripts, state["run_id"])
        
        # Update state
        state["current_stage"] = "script_generation"
        state["updated_at"] = datetime.utcnow()
        if "script_generation" not in state["stages_completed"]:
            state["stages_completed"].append("script_generation")
        state["total_tokens_used"] += tokens_used
        
        duration = (datetime.utcnow() - start_time).total_seconds()
        state["agent2_duration_seconds"] = duration
        state["total_duration_seconds"] += duration
        
        # Count scripts by language
        script_counts = {}
        for script in scripts:
            script_counts[script.language] = script_counts.get(script.language, 0) + 1
        
        logger.info(
            f"[{state['run_id']}] Script Generation completed in {duration:.2f}s, "
            f"generated {len(scripts)} scripts, used {tokens_used} tokens"
            + (f" (healing pass {healing_rounds})" if is_healing_pass else "")
        )
        
        # Add metadata for LangSmith tracing
        state["_langsmith_metadata"] = {
            **state.get("_langsmith_metadata", {}),
            "script_generation": {
                "scripts_generated": len(scripts),
                "script_counts_by_language": script_counts,
                "page_objects_created": len(state.get("page_objects", [])),
                "tokens_used": tokens_used,
                "duration_seconds": duration,
                "mock_mode": use_mock,
                "healing_pass": is_healing_pass,
                "healing_round": healing_rounds if is_healing_pass else 0,
            }
        }
        
        # -----------------------------------------------------------------
        # Self-healing loop bookkeeping: this pass consumed the healed
        # locators, so reset the loop control for the next healing round.
        # -----------------------------------------------------------------
        state["healing_pending"] = False
        
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


def _normalize_selectors(script: AutomationScript) -> AutomationScript:
    """Apply KNOWN_SELECTOR_HEALINGS to a script's content (post-generation pass)."""
    content = script.content
    for bad, good in KNOWN_SELECTOR_HEALINGS.items():
        if bad in content:
            content = content.replace(bad, good)
    if content != script.content:
        logger.info(f"Selector normalization applied to {script.file_path}")
    return script.model_copy(update={"content": content})


def _apply_healed_locators(
    scripts: List[AutomationScript],
    healing_results: List[SelectorHealingResult],
) -> List[AutomationScript]:
    """
    Apply healed locators to generated scripts (text substitution).
    
    Self-healing feedback loop (Stage 4 -> Stage 3): replaces every occurrence
    of a failed selector with its healed counterpart in all script bodies so
    the re-executed suite uses the healed locators even before Agent 2
    re-emits the scripts.
    
    Args:
        scripts: Previously generated automation scripts
        healing_results: Healed locator results from Agent 2b
    
    Returns:
        New list of scripts with healed locators applied
    """
    if not healing_results:
        return scripts
    
    patched = []
    for script in scripts:
        content = script.content
        for h in healing_results:
            old_sel = getattr(h, "failed_selector", None) or (h.alternatives or [{}])[0].get("failed_selector", "")
            if old_sel and old_sel in content:
                content = content.replace(old_sel, h.healed_selector)
        patched.append(script.model_copy(update={"content": content}))
    return patched