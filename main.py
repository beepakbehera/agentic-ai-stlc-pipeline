#!/usr/bin/env python3
"""
Agentic AI STLC Pipeline - Main Entry Point.

Executes the complete 6-stage Software Testing Life Cycle pipeline:
1. RAG Retrieval & Ingestion
2. Test Case Authoring (Agent 1: Nemotron 3 Ultra 550B)
3. Script Generation (Agent 2: Nemotron 3 Ultra 550B)
4. MCP Selector Self-Healing (Agent 2b: MCP + Nemotron)
5. CI/CD Trigger & Monitoring (Agent 3: GitHub Actions)
6. Failure Analysis & Jira Defect Logger (Agent 4: Nemotron + Jira)

Usage:
    python main.py --requirements "..." --acceptance-criteria "..." --app-context "..."
    python main.py --config config.yaml
"""

import argparse
import asyncio
import json
import logging
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Enable LangSmith tracing early (before other imports)
import os
os.environ.setdefault("LANGSMITH_TRACING", "true")
os.environ.setdefault("LANGSMITH_PROJECT", "agentic-ai-stlc-pipeline")

from src.state import create_initial_state
from src.graph import pipeline_graph, run_pipeline
from config.settings import get_settings, Settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("pipeline.log"),
    ]
)
logger = logging.getLogger(__name__)

settings = get_settings()


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Agentic AI STLC Pipeline - Automated Testing Life Cycle",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with inline parameters
  python main.py \\
    --requirements "User login with email/password" \\
    --acceptance-criteria "Valid credentials grant access; invalid show error" \\
    --app-context "Web app at https://app.example.com"

  # Run with config file
  python main.py --config pipeline_config.json

  # Run with environment variables (set in .env)
  python main.py
        """
    )
    
    # Pipeline identification
    parser.add_argument(
        "--pipeline-id",
        default=f"stlc-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}",
        help="Unique pipeline identifier",
    )
    parser.add_argument(
        "--run-id",
        default=str(uuid.uuid4())[:8],
        help="Unique run identifier",
    )
    
    # Input parameters
    parser.add_argument(
        "--requirements",
        help="Requirements/user stories text",
    )
    parser.add_argument(
        "--acceptance-criteria",
        help="Acceptance criteria text",
    )
    parser.add_argument(
        "--app-context",
        dest="application_context",
        help="Application under test context",
    )
    parser.add_argument(
        "--git-ref",
        default="main",
        help="Git reference (branch/tag/SHA)",
    )
    parser.add_argument(
        "--environment",
        default="staging",
        help="Target environment",
    )
    parser.add_argument(
        "--triggered-by",
        default="manual",
        help="Trigger source",
    )
    
    # Configuration
    parser.add_argument(
        "--config",
        help="Path to JSON config file with input parameters",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=3,
        help="Maximum retries for failed stages",
    )
    parser.add_argument(
        "--pipeline-timeout",
        type=int,
        default=3600,
        help="Pipeline timeout in seconds",
    )
    
    # Output
    parser.add_argument(
        "--output",
        help="Path to save final state JSON",
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level",
    )
    
    # Special modes
    parser.add_argument(
        "--ingest-documents",
        help="Path to documents directory for RAG ingestion",
    )
    parser.add_argument(
        "--visualize",
        action="store_true",
        help="Print pipeline graph visualization and exit",
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Run in mock mode (skip real API calls, use simulated responses)",
    )
    
    return parser.parse_args()


def load_config_file(config_path: str) -> Dict[str, Any]:
    """Load configuration from JSON file."""
    with open(config_path, "r") as f:
        return json.load(f)


def load_documents_for_ingestion(doc_path: str) -> list:
    """Load documents from directory for RAG ingestion."""
    import os
    documents = []
    path = Path(doc_path)
    
    if path.is_file():
        files = [path]
    else:
        files = list(path.rglob("*.txt")) + list(path.rglob("*.md")) + list(path.rglob("*.json"))
    
    for file_path in files:
        try:
            content = file_path.read_text(encoding="utf-8")
            documents.append({
                "content": content,
                "metadata": {
                    "source": str(file_path),
                    "type": "document",
                    "ingested_at": datetime.utcnow().isoformat(),
                }
            })
        except Exception as e:
            logger.warning(f"Failed to load {file_path}: {e}")
    
    return documents


async def run_ingestion(documents: list) -> None:
    """Run document ingestion into vector store."""
    from src.nodes.rag_retrieval import ingest_documents_node
    from src.state import create_initial_state
    
    state = create_initial_state(
        pipeline_id="ingestion",
        run_id=str(uuid.uuid4())[:8],
        requirements="",
        acceptance_criteria="",
        application_context="",
    )
    
    await ingest_documents_node(state, documents)
    logger.info(f"Ingestion complete: {len(documents)} documents processed")


async def main() -> int:
    """Main entry point."""
    args = parse_args()
    
    # Set log level
    logging.getLogger().setLevel(args.log_level)
    
    # Show visualization and exit
    if args.visualize:
        from src.graph import get_graph_visualization
        print(get_graph_visualization())
        return 0
    
    # Load config file if provided
    config_data = {}
    if args.config:
        config_data = load_config_file(args.config)
    
    # Handle document ingestion mode
    if args.ingest_documents:
        documents = load_documents_for_ingestion(args.ingest_documents)
        if documents:
            await run_ingestion(documents)
        else:
            logger.warning("No documents found for ingestion")
        return 0
    
    # Gather input parameters (CLI args override config file)
    requirements = args.requirements or config_data.get("requirements", "")
    acceptance_criteria = args.acceptance_criteria or config_data.get("acceptance_criteria", "")
    application_context = args.application_context or config_data.get("application_context", "")
    
    # Validate required inputs
    if not requirements:
        logger.error("Requirements are required. Use --requirements or --config")
        return 1
    if not acceptance_criteria:
        logger.error("Acceptance criteria are required. Use --acceptance-criteria or --config")
        return 1
    if not application_context:
        logger.error("Application context is required. Use --app-context or --config")
        return 1
    
    # Validate settings
    if not settings.nemotron_api_key.get_secret_value() and not args.mock:
        logger.error("NEMOTRON_API_KEY not configured. Check .env file or use --mock")
        return 1
    
    # Run pipeline
    logger.info(f"Starting pipeline: {args.pipeline_id}")
    logger.info(f"Run ID: {args.run_id}")
    logger.info(f"Environment: {args.environment}")
    logger.info(f"Git Ref: {args.git_ref}")
    if args.mock:
        logger.info("Running in MOCK mode - skipping real API calls")
    
    try:
        final_state = await run_pipeline(
            pipeline_id=args.pipeline_id,
            run_id=args.run_id,
            requirements=requirements,
            acceptance_criteria=acceptance_criteria,
            application_context=application_context,
            git_ref=args.git_ref,
            environment=args.environment,
            triggered_by=args.triggered_by,
            max_retries=args.max_retries,
            pipeline_timeout=args.pipeline_timeout,
            mock_mode=args.mock,
        )
        
        # Print summary
        print("\n" + "=" * 60)
        print("PIPELINE EXECUTION SUMMARY")
        print("=" * 60)
        
        if final_state is None:
            print("Pipeline failed to execute (no state returned)")
        else:
            print(f"Pipeline ID: {final_state.get('pipeline_id', 'N/A')}")
            print(f"Run ID: {final_state.get('run_id', 'N/A')}")
            print(f"Status: {final_state.get('status', 'unknown')}")
            print(f"Stages Completed: {', '.join(final_state.get('stages_completed', []))}")
            if final_state.get('stages_failed'):
                print(f"Stages Failed: {', '.join(final_state['stages_failed'])}")
            print(f"Total Duration: {final_state.get('total_duration_seconds', 0):.2f}s")
            print(f"Total Tokens Used: {final_state.get('total_tokens_used', 0)}")
            
            if final_state.get('test_suite'):
                suite = final_state['test_suite']
                print(f"\nTest Cases Generated: {len(suite.test_cases)}")
                print(f"  By Priority: {suite.summary.get('by_priority', {})}")
                print(f"  By Type: {suite.summary.get('by_type', {})}")
            
            if final_state.get('workflow_execution'):
                we = final_state['workflow_execution']
                print(f"\nCI/CD Execution:")
                print(f"  Run ID: {we.workflow_run_id}")
                print(f"  Conclusion: {we.conclusion}")
                print(f"  Test Results: {we.test_results}")
            
            if final_state.get('created_jira_issues'):
                print(f"\nJira Issues Created: {len(final_state['created_jira_issues'])}")
                for issue in final_state['created_jira_issues']:
                    print(f"  - {issue.get('key')}: {issue.get('fields', {}).get('summary')}")
        
        if final_state.get('errors'):
            print(f"\nErrors: {len(final_state['errors'])}")
            for err in final_state['errors']:
                print(f"  - [{err['stage']}] {err['error']}")
        
        # Save output if requested
        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Convert state to serializable format
            output_data = {
                "pipeline_id": final_state["pipeline_id"],
                "run_id": final_state["run_id"],
                "status": final_state["status"],
                "stages_completed": final_state["stages_completed"],
                "stages_failed": final_state["stages_failed"],
                "total_duration_seconds": final_state["total_duration_seconds"],
                "total_tokens_used": final_state["total_tokens_used"],
                "test_cases_count": len(final_state.get("test_suite", {}).test_cases) if final_state.get("test_suite") else 0,
                "jira_issues_created": len(final_state.get("created_jira_issues", [])),
                "errors": final_state["errors"],
            }
            
            output_path.write_text(json.dumps(output_data, indent=2, default=str))
            logger.info(f"Results saved to {output_path}")
        
        return 0 if final_state and final_state.get("status") == "completed" else 1
        
    except KeyboardInterrupt:
        logger.info("Pipeline interrupted by user")
        return 130
    except Exception as e:
        logger.exception(f"Pipeline failed with exception: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))