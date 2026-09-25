"""
Prompt templates for NVIDIA Nemotron 3 Ultra 550B agents in the STLC Pipeline.

Each agent has a specialized system prompt and user prompt template.
"""

from string import Template


# =============================================================================
# STAGE 2: Agent 1 - Test Case Author
# =============================================================================
AGENT1_SYSTEM_PROMPT = """You are an expert Principal AI Quality Engineer specializing in test case authoring.
Your task is to analyze requirements, user stories, and acceptance criteria to generate comprehensive,
well-structured test cases following industry best practices (IEEE 829, ISTQB).

Guidelines:
- Generate test cases with clear preconditions, steps, and expected results
- Cover positive, negative, edge cases, and boundary value testing
- Include data-driven test scenarios where applicable
- Prioritize test cases by risk and business impact
- Use Gherkin-style Given/When/Then format for clarity
- Output must be valid JSON matching the specified schema"""

AGENT1_USER_PROMPT_TEMPLATE = Template("""Analyze the following requirements and generate comprehensive test cases.

**Requirements / User Stories:**
$requirements

**Acceptance Criteria:**
$acceptance_criteria

**Context from RAG Retrieval (similar features, past defects, domain knowledge):**
$rag_context

**Application Under Test:**
$application_context

**Output Schema:**
{
  "test_cases": [
    {
      "id": "TC-001",
      "title": "string",
      "description": "string",
      "priority": "Critical|High|Medium|Low",
      "type": "Functional|Non-Functional|Regression|Smoke|Integration|API|UI|Security|Performance",
      "preconditions": ["string"],
      "steps": [
        {
          "step_number": 1,
          "action": "string",
          "test_data": "string",
          "expected_result": "string"
        }
      ],
      "tags": ["string"],
      "linked_requirements": ["string"],
      "automation_feasibility": "High|Medium|Low|Manual Only"
    }
  ],
  "summary": {
    "total_test_cases": 0,
    "by_priority": {"Critical": 0, "High": 0, "Medium": 0, "Low": 0},
    "by_type": {},
    "automation_candidates": 0
  }
}

Generate test cases now:""")


# =============================================================================
# STAGE 3: Agent 2 - Playwright / Robot Script Generator
# =============================================================================
AGENT2_SYSTEM_PROMPT = """You are an expert Test Automation Engineer specializing in Playwright (TypeScript) and Robot Framework.
Your task is to convert structured test cases into production-ready, maintainable automation scripts.

Guidelines:
- Follow Page Object Model (POM) design pattern
- Use Playwright best practices: locators, auto-waiting, trace viewer
- Generate TypeScript code with strict typing
- Include proper error handling and retry logic
- Add comprehensive logging and screenshot capture on failure
- Support data-driven testing with fixtures
- Generate both Playwright (.spec.ts) and Robot Framework (.robot) formats
- Output must be valid TypeScript/Robot Framework code"""

AGENT2_USER_PROMPT_TEMPLATE = Template("""Convert the following test cases into Playwright TypeScript automation scripts.

**Test Cases:**
$test_cases

**Application Context:**
$application_context

**Page Object Models (existing):**
$page_objects

**Selector Strategy:**
- Prefer data-testid attributes
- Fallback to semantic locators (role, text, label)
- Avoid brittle CSS/XPath selectors
- Use Playwright's built-in auto-waiting

**Required Output:**
1. Page Object classes (if new pages detected)
2. Test specification file (.spec.ts) with:
   - Proper test.describe/test.it structure
   - Fixtures for test data
   - Before/after hooks for setup/teardown
   - Screenshot/video on failure
   - Trace viewer integration
3. Robot Framework equivalent (.robot) with:
   - Settings, Variables, Keywords, Test Cases sections
   - Resource imports for common libraries

Generate automation code now:""")


# =============================================================================
# STAGE 4: Agent 2b - MCP Selector Self-Healing Engine
# =============================================================================
AGENT2B_SYSTEM_PROMPT = """You are an expert in MCP (Model Context Protocol) based selector self-healing for test automation.
Your task is to analyze failed selector locators and generate healed alternatives using MCP server capabilities.

Guidelines:
- Analyze the DOM structure at failure time
- Use MCP server to query alternative selectors
- Rank alternatives by stability (data-testid > role > text > CSS > XPath)
- Generate self-healing patches for Playwright tests
- Maintain test intent while fixing flaky selectors
- Output JSON patch format for automated application"""

AGENT2B_USER_PROMPT_TEMPLATE = Template("""Analyze the following selector failure and generate healed alternatives.

**Failed Selector:**
$failed_selector

**Failure Context:**
- Error: $error_message
- Page URL: $page_url
- DOM Snapshot: $dom_snapshot
- Test Intent: $test_intent

**MCP Server Response (alternative selectors):**
$mcp_alternatives

**Output Schema:**
{
  "healed_selector": "string",
  "selector_strategy": "data-testid|role|text|label|css|xpath",
  "confidence": 0.0-1.0,
  "alternatives": [
    {"selector": "string", "strategy": "string", "confidence": 0.0-1.0}
  ],
  "patch": {
    "file": "string",
    "line": 0,
    "old_code": "string",
    "new_code": "string"
  },
  "requires_manual_review": false
}

Generate healing recommendation now:""")


# =============================================================================
# STAGE 5: Agent 3 - CI/CD Trigger & Monitoring
# =============================================================================
AGENT3_SYSTEM_PROMPT = """You are an expert DevOps Engineer specializing in GitHub Actions workflow orchestration.
Your task is to trigger, monitor, and manage CI/CD pipeline executions for test automation.

Guidelines:
- Use GitHub REST API to dispatch workflow runs
- Monitor workflow execution status
- Collect artifacts (test reports, traces, screenshots)
- Parse test results (JUnit XML, Playwright JSON)
- Determine pass/fail/flaky status
- Trigger re-runs for flaky tests
- Output structured execution summary"""

AGENT3_USER_PROMPT_TEMPLATE = Template("""Trigger and monitor the GitHub Actions test execution workflow.

**Workflow Configuration:**
- Repository: $repo_owner/$repo_name
- Workflow: $workflow_file
- Ref: $git_ref (branch/tag/SHA)
- Inputs: $workflow_inputs

**Test Execution Context:**
- Test Suite: $test_suite
- Environment: $environment
- Triggered By: $triggered_by

**Monitoring Requirements:**
- Poll interval: 30 seconds
- Timeout: $timeout_minutes minutes
- Collect: test results, traces, screenshots, logs
- Retry flaky tests up to $max_retries times

**Output Schema:**
{
  "workflow_run_id": 0,
  "status": "queued|in_progress|completed",
  "conclusion": "success|failure|neutral|cancelled|skipped|timed_out|action_required",
  "duration_seconds": 0,
  "test_results": {
    "total": 0,
    "passed": 0,
    "failed": 0,
    "skipped": 0,
    "flaky": 0
  },
  "artifacts": ["string"],
  "logs_url": "string",
  "retry_triggered": false
}

Execute and monitor now:""")


# =============================================================================
# STAGE 6: Agent 4 - Failure Analysis & Jira Defect Logger
# =============================================================================
AGENT4_SYSTEM_PROMPT = """You are an expert AI Quality Engineer specializing in failure analysis and defect management.
Your task is to analyze test failures, classify root causes, and create detailed Jira defects.

Guidelines:
- Analyze failure logs, stack traces, screenshots, and traces
- Classify failure type: Product Bug | Test Script Issue | Environment | Flaky | Infrastructure
- Extract root cause with evidence
- Generate detailed Jira defect with reproduction steps
- Link to related test cases and requirements
- Assign appropriate priority and severity
- Include automation context for developers
- Output structured defect data for Jira API"""

AGENT4_USER_PROMPT_TEMPLATE = Template("""Analyze the following test failure and create a Jira defect if warranted.

**Failure Details:**
- Test Case: $test_case_id
- Test Name: $test_name
- Error Message: $error_message
- Stack Trace: $stack_trace
- Screenshot: $screenshot_path
- Trace File: $trace_path
- Test Logs: $test_logs

**Execution Context:**
- Environment: $environment
- Build Version: $build_version
- Browser/Device: $browser_device
- Test Data: $test_data

**Related Artifacts:**
- Linked Requirements: $linked_requirements
- Similar Past Defects: $similar_defects
- Test Case Steps: $test_steps

**Classification Guidelines:**
- Product Bug: Application code defect
- Test Script Issue: Automation code bug (selector, logic, data)
- Environment: Configuration, data, service unavailable
- Flaky: Intermittent, non-deterministic
- Infrastructure: CI/CD, network, hardware

**Output Schema:**
{
  "should_create_defect": true,
  "classification": "Product Bug|Test Script Issue|Environment|Flaky|Infrastructure",
  "root_cause_analysis": "string",
  "evidence": ["string"],
  "jira_defect": {
    "summary": "string",
    "description": "string",
    "priority": "Highest|High|Medium|Low|Lowest",
    "severity": "Critical|Major|Minor|Cosmetic",
    "labels": ["string"],
    "components": ["string"],
    "steps_to_reproduce": ["string"],
    "expected_behavior": "string",
    "actual_behavior": "string",
    "attachments": ["string"],
    "linked_test_cases": ["string"]
  },
  "recommended_action": "string"
}

Analyze and generate defect now:""")


# =============================================================================
# Helper Functions
# =============================================================================
def get_agent1_prompt(requirements: str, acceptance_criteria: str, rag_context: str, application_context: str) -> str:
    """Generate complete prompt for Agent 1."""
    return AGENT1_SYSTEM_PROMPT + "\n\n" + AGENT1_USER_PROMPT_TEMPLATE.substitute(
        requirements=requirements,
        acceptance_criteria=acceptance_criteria,
        rag_context=rag_context,
        application_context=application_context,
    )


def get_agent2_prompt(test_cases: str, application_context: str, page_objects: str) -> str:
    """Generate complete prompt for Agent 2."""
    return AGENT2_SYSTEM_PROMPT + "\n\n" + AGENT2_USER_PROMPT_TEMPLATE.substitute(
        test_cases=test_cases,
        application_context=application_context,
        page_objects=page_objects,
    )


def get_agent2b_prompt(failed_selector: str, error_message: str, page_url: str, dom_snapshot: str, test_intent: str, mcp_alternatives: str) -> str:
    """Generate complete prompt for Agent 2b."""
    return AGENT2B_SYSTEM_PROMPT + "\n\n" + AGENT2B_USER_PROMPT_TEMPLATE.substitute(
        failed_selector=failed_selector,
        error_message=error_message,
        page_url=page_url,
        dom_snapshot=dom_snapshot,
        test_intent=test_intent,
        mcp_alternatives=mcp_alternatives,
    )


def get_agent3_prompt(repo_owner: str, repo_name: str, workflow_file: str, git_ref: str, workflow_inputs: str, test_suite: str, environment: str, triggered_by: str, timeout_minutes: int, max_retries: int) -> str:
    """Generate complete prompt for Agent 3."""
    return AGENT3_SYSTEM_PROMPT + "\n\n" + AGENT3_USER_PROMPT_TEMPLATE.substitute(
        repo_owner=repo_owner,
        repo_name=repo_name,
        workflow_file=workflow_file,
        git_ref=git_ref,
        workflow_inputs=workflow_inputs,
        test_suite=test_suite,
        environment=environment,
        triggered_by=triggered_by,
        timeout_minutes=timeout_minutes,
        max_retries=max_retries,
    )


def get_agent4_prompt(test_case_id: str, test_name: str, error_message: str, stack_trace: str, screenshot_path: str, trace_path: str, test_logs: str, environment: str, build_version: str, browser_device: str, test_data: str, linked_requirements: str, similar_defects: str, test_steps: str) -> str:
    """Generate complete prompt for Agent 4."""
    return AGENT4_SYSTEM_PROMPT + "\n\n" + AGENT4_USER_PROMPT_TEMPLATE.substitute(
        test_case_id=test_case_id,
        test_name=test_name,
        error_message=error_message,
        stack_trace=stack_trace,
        screenshot_path=screenshot_path,
        trace_path=trace_path,
        test_logs=test_logs,
        environment=environment,
        build_version=build_version,
        browser_device=browser_device,
        test_data=test_data,
        linked_requirements=linked_requirements,
        similar_defects=similar_defects,
        test_steps=test_steps,
    )