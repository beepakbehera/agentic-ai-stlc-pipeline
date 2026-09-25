"""
Stage 4: Agent 2b - MCP Selector Self-Healing Engine Node.

Uses MCP (Model Context Protocol) server to analyze failed selectors
and generate healed alternatives for test automation.
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

import httpx
from pydantic import ValidationError

from src.state import AgenticSTLCState, SelectorHealingResult
from config.settings import get_settings
from config.prompt_templates import get_agent2b_prompt

logger = logging.getLogger(__name__)
settings = get_settings()


class MCPHealingClient:
    """Client for MCP Selector Self-Healing Server."""
    
    def __init__(self):
        self.base_url = settings.mcp_server_url.rstrip("/")
        self.timeout = settings.mcp_timeout
        self.client = httpx.AsyncClient(timeout=self.timeout)
    
    async def get_alternatives(self, failed_selector: str, dom_snapshot: str, page_url: str) -> List[Dict[str, Any]]:
        """
        Query MCP server for alternative selectors.
        
        Args:
            failed_selector: The selector that failed
            dom_snapshot: DOM snapshot at failure time
            page_url: Page URL where failure occurred
            
        Returns:
            List of alternative selector suggestions
        """
        try:
            response = await self.client.post(
                f"{self.base_url}/heal",
                json={
                    "failed_selector": failed_selector,
                    "dom_snapshot": dom_snapshot,
                    "page_url": page_url,
                },
            )
            response.raise_for_status()
            return response.json().get("alternatives", [])
        except Exception as e:
            logger.warning(f"MCP server query failed: {e}")
            return []


# Global client instance
mcp_client = MCPHealingClient()


class Agent2BHealingEngine:
    """Agent 2b: Selector Self-Healing using Nemotron + MCP."""
    
    def __init__(self):
        self.api_key = settings.nemotron_api_key.get_secret_value()
        self.base_url = settings.nemotron_base_url.rstrip("/")
        self.model = settings.nemotron_model
        self.temperature = settings.nemotron_temperature
        self.max_tokens = settings.nemotron_max_tokens
        self.client = httpx.AsyncClient(timeout=120.0)
    
    async def heal_selector(self, prompt: str) -> Dict[str, Any]:
        """
        Call Nemotron API to generate healing recommendation.
        
        Args:
            prompt: Complete prompt for selector healing
            
        Returns:
            Parsed JSON response with healing result
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are an expert in MCP-based selector self-healing."},
                {"role": "user", "content": prompt},
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "response_format": {"type": "json_object"},
        }
        
        response = await self.client.post(
            f"{self.base_url}/chat/completions",
            headers=headers,
            json=payload,
        )
        response.raise_for_status()
        
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        tokens_used = data.get("usage", {}).get("total_tokens", 0)
        
        return json.loads(content), tokens_used


# Global agent instance
agent2b = Agent2BHealingEngine()


async def agent2b_mcp_heal_node(state: AgenticSTLCState) -> AgenticSTLCState:
    """
    LangGraph node for MCP Selector Self-Healing (Agent 2b).
    
    Analyzes failed selectors from test execution and generates
    healed alternatives using MCP server and Nemotron 3 Ultra 550B.
    """
    logger.info(f"[{state['run_id']}] Starting Stage 4: Selector Self-Healing (Agent 2b)")
    start_time = datetime.utcnow()
    
    try:
        # Get failed selectors from state (populated by previous test run)
        failed_selectors = state.get("failed_selectors", [])
        
        if not failed_selectors:
            logger.info(f"[{state['run_id']}] No failed selectors to heal, skipping")
            state["current_stage"] = "selector_healing"
            state["updated_at"] = datetime.utcnow()
            state["stages_completed"].append("selector_healing")
            return state
        
        healing_results = []
        total_tokens = 0
        
        for failure in failed_selectors:
            failed_selector = failure.get("selector", "")
            error_message = failure.get("error", "")
            page_url = failure.get("page_url", "")
            dom_snapshot = failure.get("dom_snapshot", "")
            test_intent = failure.get("test_intent", "")
            
            # Query MCP server for alternatives
            mcp_alternatives = await mcp_client.get_alternatives(
                failed_selector, dom_snapshot, page_url
            )
            state["mcp_responses"].append({
                "failed_selector": failed_selector,
                "alternatives": mcp_alternatives,
            })
            
            # Generate healing recommendation with Nemotron
            prompt = get_agent2b_prompt(
                failed_selector=failed_selector,
                error_message=error_message,
                page_url=page_url,
                dom_snapshot=dom_snapshot[:5000] if dom_snapshot else "",
                test_intent=test_intent,
                mcp_alternatives=json.dumps(mcp_alternatives, indent=2),
            )
            state["agent2b_prompt"] = prompt
            
            response_data, tokens_used = await agent2b.heal_selector(prompt)
            state["agent2b_response"] = json.dumps(response_data, indent=2)
            total_tokens += tokens_used
            
            # Parse healing result
            healing_result = SelectorHealingResult(**response_data)
            healing_results.append(healing_result)
        
        state["healing_results"] = healing_results
        state["agent2b_tokens_used"] = total_tokens
        
        # Update state
        state["current_stage"] = "selector_healing"
        state["updated_at"] = datetime.utcnow()
        state["stages_completed"].append("selector_healing")
        state["total_tokens_used"] += total_tokens
        
        duration = (datetime.utcnow() - start_time).total_seconds()
        state["agent2b_duration_seconds"] = duration
        state["total_duration_seconds"] += duration
        
        logger.info(f"[{state['run_id']}] Selector Healing completed in {duration:.2f}s, healed {len(healing_results)} selectors, used {total_tokens} tokens")
        
    except ValidationError as e:
        logger.error(f"[{state['run_id']}] Selector healing validation failed: {e}")
        state["errors"].append({
            "stage": "selector_healing",
            "error": f"Validation error: {e}",
            "timestamp": datetime.utcnow().isoformat(),
        })
        state["stages_failed"].append("selector_healing")
    except Exception as e:
        logger.error(f"[{state['run_id']}] Selector Healing failed: {e}")
        state["errors"].append({
            "stage": "selector_healing",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        })
        state["stages_failed"].append("selector_healing")
    
    return state