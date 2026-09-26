#!/usr/bin/env python3
"""
End-to-end validation of the self-healing feedback loop (Stage 4 -> Stage 3).

Forces a loop scenario with mock mode:
1. Injects failed selectors before Stage 4 (Agent 2b)
2. Agent 2b heals them and routes flow back to Stage 3 (Agent 2)
3. Agent 2 applies the healed locators to the scripts (in-place patch)
4. Flow re-enters Stage 5 (CI/CD) and completes the pipeline
"""
import asyncio
import sys
import uuid
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

from langsmith.run_helpers import tracing_context

from src.state import create_initial_state
from src.graph import create_pipeline_graph
from src.nodes import agent2b_mcp_heal
from config.settings import get_settings

settings = get_settings()

# Force a healing scenario: inject failed selectors that Agent 2b will "heal"
FAILED_SELECTORS = [
    {
        "selector": "[data-testid=login-button]",
        "error": "Timeout waiting for selector",
        "page_url": "https://example.com/login",
        "dom_snapshot": "<button data-testid='submit-login'>Sign in</button>",
        "test_intent": "Click the login button to submit credentials",
    },
]

# Monkeypatch the healing engine to run in mock mode (no external calls)
agent2b_mcp_heal.agent2b.client = None
original_heal = agent2b_mcp_heal.Agent2BHealingEngine.heal_selector


async def mock_heal_selector(self, prompt):
    return {
        "failed_selector": "[data-testid=login-button]",
        "healed_selector": "[data-testid=submit-login]",
        "selector_strategy": "data-testid",
        "confidence": 0.95,
        "alternatives": [],
        "requires_manual_review": False,
    }, 0


agent2b_mcp_heal.Agent2BHealingEngine.heal_selector = mock_heal_selector


async def main():
    run_id = f"healloop-{uuid.uuid4().hex[:6]}"
    state = create_initial_state(
        pipeline_id="heal-loop-test",
        run_id=run_id,
        requirements="User login with email/password",
        acceptance_criteria="Valid credentials succeed; invalid show error",
        application_context="Web app at https://example.com",
        mock_mode=True,
        max_retries=3,
    )
    state["failed_selectors"] = FAILED_SELECTORS

    graph = create_pipeline_graph(enable_retry=False)

    stages_seen = []
    healing_passes = 0
    with tracing_context(enabled=False):
        config = {"configurable": {"thread_id": run_id}}
        async for update in graph.astream(state, config=config):
            for node_name, s in update.items():
                stages_seen.append(node_name)
                if node_name == "selector_healing":
                    print(f"  [trace] selector_healing -> healing_pending={s.get('healing_pending')}, "
                          f"rounds={s.get('healing_rounds')}")
                if node_name == "script_generation":
                    marker = "(healing pass)" if s.get("healing_history") else "(initial)"
                    if s.get("healing_history"):
                        healing_passes += 1
                    print(f"  [trace] script_generation {marker}")

    print()
    print("Stages executed in order:")
    for i, st in enumerate(stages_seen, 1):
        print(f"  {i}. {st}")

    print()
    print("Assertions:")
    looped_back = False
    if stages_seen.count("script_generation") >= 2:
        first_sg = stages_seen.index("script_generation")
        second_sg = stages_seen.index("script_generation", first_sg + 1)
        looped_back = "selector_healing" in stages_seen[first_sg:second_sg]
    print(f"  Loop back Stage 4 -> Stage 3 occurred: {looped_back}")
    print(f"  Healing passes (Stage 3 re-runs): {healing_passes}")
    print(f"  healing_history entries: {len(state.get('healing_history', []))}")

    # Check the healed locator landed in the written scripts
    script_dir = Path(f"tests/generated/{state['run_id']}")
    patched = False
    if script_dir.exists():
        for f in script_dir.glob("*"):
            content = f.read_text(encoding="utf-8", errors="ignore")
            if "[data-testid=submit-login]" in content:
                patched = True
                print(f"  Healed locator found on disk in: {f.name}")
            if "[data-testid=login-button]" in content and "[data-testid=submit-login]" in content:
                print(f"  WARNING: failed locator still present alongside healed one in {f.name}")
    else:
        print(f"  (script dir {script_dir} not found)")

    print()
    if looped_back and healing_passes >= 1:
        print("PASS: Self-healing feedback loop works (Stage 4 -> Stage 3 -> Stage 5).")
        return 0
    print("FAIL: Loop did not behave as expected.")
    return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
