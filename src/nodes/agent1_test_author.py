"""
Stage 2: Agent 1 - Test Case Author Node.

Uses NVIDIA Nemotron 3 Ultra 550B to generate comprehensive test cases
from requirements and RAG context.
"""

import json
import logging
import time
from datetime import datetime
from typing import Dict, Any

import httpx
from pydantic import ValidationError

from src.state import AgenticSTLCState, TestSuite, TestCase
from config.settings import get_settings
from config.prompt_templates import get_agent1_prompt

logger = logging.getLogger(__name__)
settings = get_settings()


class Agent1TestAuthor:
    """Agent 1: Test Case Author using Nemotron 3 Ultra 550B."""
    
    def __init__(self):
        self.api_key = settings.nemotron_api_key.get_secret_value()
        self.base_url = settings.nemotron_base_url.rstrip("/")
        self.model = settings.nemotron_model
        self.temperature = settings.nemotron_temperature
        self.max_tokens = settings.nemotron_max_tokens
        self.client = httpx.AsyncClient(timeout=120.0)
    
    async def generate_test_cases(self, prompt: str) -> Dict[str, Any]:
        """
        Call Nemotron API to generate test cases.
        
        Args:
            prompt: Complete prompt for test case generation
            
        Returns:
            Parsed JSON response with test cases
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are an expert Principal AI Quality Engineer."},
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
agent1 = Agent1TestAuthor()


async def agent1_test_author_node(state: AgenticSTLCState) -> AgenticSTLCState:
    """
    LangGraph node for Test Case Authoring (Agent 1).
    
    Generates comprehensive test cases using Nemotron 3 Ultra 550B
    based on requirements, acceptance criteria, and RAG context.
    """
    logger.info(f"[{state['run_id']}] Starting Stage 2: Test Case Authoring (Agent 1)")
    start_time = datetime.utcnow()
    
    try:
        # Build RAG context string
        rag_context_parts = []
        if state["similar_features"]:
            rag_context_parts.append("**Similar Features:**\n" + "\n".join(state["similar_features"]))
        if state["past_defects"]:
            rag_context_parts.append("**Past Defects:**\n" + "\n".join(state["past_defects"]))
        if state["domain_knowledge"]:
            rag_context_parts.append("**Domain Knowledge:**\n" + "\n".join(state["domain_knowledge"]))
        rag_context = "\n\n".join(rag_context_parts) if rag_context_parts else "No prior context available."
        
        # Generate prompt
        prompt = get_agent1_prompt(
            requirements=state["requirements"],
            acceptance_criteria=state["acceptance_criteria"],
            rag_context=rag_context,
            application_context=state["application_context"],
        )
        state["agent1_prompt"] = prompt
        
        # Call Nemotron API
        response_data, tokens_used = await agent1.generate_test_cases(prompt)
        state["agent1_response"] = json.dumps(response_data, indent=2)
        state["agent1_tokens_used"] = tokens_used
        
        # Parse and validate test suite
        test_suite = TestSuite(**response_data)
        state["test_suite"] = test_suite
        
        # Update state
        state["current_stage"] = "test_authoring"
        state["updated_at"] = datetime.utcnow()
        state["stages_completed"].append("test_authoring")
        state["total_tokens_used"] += tokens_used
        
        duration = (datetime.utcnow() - start_time).total_seconds()
        state["agent1_duration_seconds"] = duration
        state["total_duration_seconds"] += duration
        
        logger.info(f"[{state['run_id']}] Test Authoring completed in {duration:.2f}s, generated {len(test_suite.test_cases)} test cases, used {tokens_used} tokens")
        
    except ValidationError as e:
        logger.error(f"[{state['run_id']}] Test case validation failed: {e}")
        state["errors"].append({
            "stage": "test_authoring",
            "error": f"Validation error: {e}",
            "timestamp": datetime.utcnow().isoformat(),
        })
        state["stages_failed"].append("test_authoring")
        state["status"] = "failed"
    except Exception as e:
        logger.error(f"[{state['run_id']}] Test Authoring failed: {e}")
        state["errors"].append({
            "stage": "test_authoring",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        })
        state["stages_failed"].append("test_authoring")
        state["status"] = "failed"
    
    return state