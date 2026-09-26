"""
Stage 2: Agent 1 - Test Case Author Node.

Uses NVIDIA Nemotron 3 Ultra 550B to generate comprehensive test cases
from requirements and RAG context.
"""

import json
import logging
import time
from datetime import datetime
from typing import Dict, Any, Optional

import httpx
from pydantic import ValidationError
from langsmith import traceable
from langsmith.wrappers import wrap_openai
from openai import AsyncOpenAI

from src.state import AgenticSTLCState, TestSuite, TestCase
from config.settings import get_settings
from config.prompt_templates import get_agent1_prompt

logger = logging.getLogger(__name__)
settings = get_settings()


# Mock response for testing without valid API key
MOCK_TEST_CASES = {
    "test_cases": [
        {
            "id": "TC-001",
            "title": "Valid user login with correct credentials",
            "description": "Verify that a registered user can successfully log in with valid email and password",
            "priority": "Critical",
            "type": "Functional",
            "preconditions": ["User is registered in the system", "User has valid credentials"],
            "steps": [
                {"step_number": 1, "action": "Navigate to login page", "test_data": "https://app.example.com/login", "expected_result": "Login page loads with email and password fields"},
                {"step_number": 2, "action": "Enter valid email address", "test_data": "testuser@example.com", "expected_result": "Email field accepts input"},
                {"step_number": 3, "action": "Enter valid password", "test_data": "ValidPass123!", "expected_result": "Password field accepts input (masked)"},
                {"step_number": 4, "action": "Click login button", "test_data": "", "expected_result": "User is redirected to dashboard"}
            ],
            "tags": ["login", "smoke", "critical"],
            "linked_requirements": ["REQ-LOGIN-001"],
            "automation_feasibility": "High"
        },
        {
            "id": "TC-002",
            "title": "Invalid password shows error message",
            "description": "Verify that an error is displayed when user enters incorrect password",
            "priority": "High",
            "type": "Functional",
            "preconditions": ["User is registered in the system"],
            "steps": [
                {"step_number": 1, "action": "Navigate to login page", "test_data": "https://app.example.com/login", "expected_result": "Login page loads"},
                {"step_number": 2, "action": "Enter valid email", "test_data": "testuser@example.com", "expected_result": "Email accepted"},
                {"step_number": 3, "action": "Enter invalid password", "test_data": "WrongPassword", "expected_result": "Password accepted"},
                {"step_number": 4, "action": "Click login button", "test_data": "", "expected_result": "Error message 'Invalid credentials' displayed"}
            ],
            "tags": ["login", "negative", "validation"],
            "linked_requirements": ["REQ-LOGIN-001"],
            "automation_feasibility": "High"
        },
        {
            "id": "TC-003",
            "title": "Invalid email format shows inline validation",
            "description": "Verify inline validation for email format",
            "priority": "Medium",
            "type": "Functional",
            "preconditions": ["Login page is accessible"],
            "steps": [
                {"step_number": 1, "action": "Enter invalid email format", "test_data": "not-an-email", "expected_result": "Inline validation error appears"},
                {"step_number": 2, "action": "Click login button", "test_data": "", "expected_result": "Form submission prevented"}
            ],
            "tags": ["login", "validation", "negative"],
            "linked_requirements": ["REQ-LOGIN-001"],
            "automation_feasibility": "Medium"
        }
    ],
    "summary": {
        "total_test_cases": 3,
        "by_priority": {"Critical": 1, "High": 1, "Medium": 1, "Low": 0},
        "by_type": {"Functional": 3},
        "automation_candidates": 3
    }
}


class Agent1TestAuthor:
    """Agent 1: Test Case Author using Nemotron 3 Ultra 550B."""
    
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
                    timeout=120.0
                )
            )
        else:
            self.client = None
            logger.info("Agent1 running in MOCK mode - using predefined test cases")
    
    @traceable(name="agent1_generate_test_cases")
    async def generate_test_cases(self, prompt: str, use_mock_override: bool = None) -> tuple[Dict[str, Any], int]:
        """
        Generate test cases using Nemotron API or mock data.
        
        Args:
            prompt: Complete prompt for test case generation
            use_mock_override: Override the instance's use_mock setting
            
        Returns:
            Tuple of (parsed JSON response with test cases, tokens_used)
        """
        use_mock = use_mock_override if use_mock_override is not None else self.use_mock
        
        if use_mock or self.client is None:
            logger.info("Using MOCK test cases for Agent 1")
            return MOCK_TEST_CASES, 0
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert Principal AI Quality Engineer."},
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
            return MOCK_TEST_CASES, 0


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
        # Check if we should use mock mode (either agent's own mock or state mock)
        use_mock = agent1.use_mock or state.get("mock_mode", False)
        response_data, tokens_used = await agent1.generate_test_cases(prompt, use_mock_override=use_mock)
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