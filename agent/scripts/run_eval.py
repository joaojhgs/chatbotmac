"""Evaluation script for agent responses using LLM-as-a-judge."""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.agent import create_macbook_agent

# Import evaluators from the same directory
# Add scripts directory to path for direct import
scripts_dir = os.path.dirname(os.path.abspath(__file__))
if scripts_dir not in sys.path:
    sys.path.insert(0, scripts_dir)

from evaluators import (
    accuracy_evaluator,
    groundedness_evaluator,
    utilization_evaluator,
)

# Load environment variables
load_dotenv()


def load_dataset(dataset_path: str) -> dict[str, Any]:
    """
    Load test dataset from JSON file.

    Args:
        dataset_path: Path to the dataset JSON file

    Returns:
        Dictionary containing test cases
    """
    with open(dataset_path, "r", encoding="utf-8") as f:
        return json.load(f)


async def run_agent_with_context(agent, question: str) -> dict[str, Any]:
    """
    Run agent and capture all tool calls and results.

    Args:
        agent: LangChain agent executor
        question: User question to ask the agent

    Returns:
        Dictionary with output and tool_context
    """
    tool_calls: list[dict[str, Any]] = []
    final_output = ""
    tool_call_tracker: dict[str, dict[str, Any]] = {}  # Track tool calls by run_id

    # Prepare agent input
    agent_input = {
        "input": question,
        "chat_history": [],  # No chat history for evaluation
    }

    try:
        # Process agent events to capture tool calls and final output
        async for event in agent.astream_events(agent_input, version="v2"):
            event_type = event.get("event")
            name = event.get("name", "")
            run_id = event.get("run_id", "")

            # Handle tool start
            if event_type == "on_tool_start":
                tool_name = event.get("name", "unknown")
                tool_input = event.get("data", {}).get("input", {})
                tool_call_tracker[run_id] = {
                    "tool_name": tool_name,
                    "input": tool_input,
                    "result": None,
                }

            # Handle tool end
            elif event_type == "on_tool_end":
                tool_name = event.get("name", "unknown")
                tool_output = event.get("data", {}).get("output", "")
                tool_result_str = str(tool_output)[:2000]  # Limit result length

                if run_id in tool_call_tracker:
                    tool_call_tracker[run_id]["result"] = tool_result_str
                else:
                    # Fallback if we missed the start event
                    tool_call_tracker[run_id] = {
                        "tool_name": tool_name,
                        "input": {},
                        "result": tool_result_str,
                    }

            # Handle final agent output
            elif event_type == "on_chain_end" and name == "AgentExecutor":
                output = event.get("data", {}).get("output", {})
                if isinstance(output, dict) and "output" in output:
                    final_output = str(output["output"])
                elif isinstance(output, str):
                    final_output = output

    except Exception as e:
        print(f"Error running agent: {e}")
        import traceback

        traceback.print_exc()
        final_output = f"Error: {str(e)}"

    # Convert tracker to list format
    tool_calls = list(tool_call_tracker.values())

    return {
        "output": final_output,
        "tool_context": tool_calls,
    }


async def evaluate_test_case(
    agent, test_case: dict[str, Any], test_num: int, total: int
) -> dict[str, Any]:
    """
    Evaluate a single test case.

    Args:
        agent: LangChain agent executor
        test_case: Test case dictionary
        test_num: Current test case number
        total: Total number of test cases

    Returns:
        Evaluation results dictionary
    """
    test_id = test_case.get("id", f"test_{test_num}")
    question = test_case.get("question", "")

    print(f"\n{'=' * 80}")
    print(f"Test {test_num}/{total}: {test_id}")
    print(f"Question: {question}")
    print(f"{'=' * 80}")

    # Run agent and capture context
    print("\n[1/4] Running agent...")
    agent_result = await run_agent_with_context(agent, question)

    print(f"Response length: {len(agent_result['output'])} characters")
    print(f"Tool calls: {len(agent_result['tool_context'])}")
    for i, tool_call in enumerate(agent_result["tool_context"], 1):
        tool_name = tool_call.get("tool_name", "unknown")
        print(f"  {i}. {tool_name}")

    # Run evaluators
    print("\n[2/4] Evaluating accuracy...")
    accuracy_result = accuracy_evaluator(test_case, agent_result, agent_result["tool_context"])

    print("\n[3/4] Evaluating information utilization...")
    utilization_result = utilization_evaluator(
        test_case, agent_result, agent_result["tool_context"]
    )

    print("\n[4/4] Evaluating groundedness...")
    groundedness_result = groundedness_evaluator(
        test_case, agent_result, agent_result["tool_context"]
    )

    # Compile results
    result = {
        "test_id": test_id,
        "question": question,
        "agent_output": agent_result["output"][:500] + "..." if len(agent_result["output"]) > 500 else agent_result["output"],
        "tool_calls_count": len(agent_result["tool_context"]),
        "tool_calls": [
            {
                "tool_name": tc.get("tool_name"),
                "input": str(tc.get("input", {}))[:200],
            }
            for tc in agent_result["tool_context"]
        ],
        "evaluations": {
            "accuracy": {
                "score": accuracy_result["score"],
                "explanation": accuracy_result["explanation"],
            },
            "utilization": {
                "score": utilization_result["score"],
                "percentage_used": utilization_result["percentage_used"],
                "explanation": utilization_result["explanation"],
            },
            "groundedness": {
                "grounded": groundedness_result["grounded"],
                "score": groundedness_result["score"],
                "explanation": groundedness_result["explanation"],
            },
        },
    }

    # Print summary
    print(f"\n{'─' * 80}")
    print("EVALUATION RESULTS:")
    print(f"{'─' * 80}")
    print(f"Accuracy: {accuracy_result['score']}/5")
    print(f"  {accuracy_result['explanation'][:200]}...")
    print(f"\nUtilization: {utilization_result['score']}/5 ({utilization_result['percentage_used']:.1f}%)")
    print(f"  {utilization_result['explanation'][:200]}...")
    print(f"\nGroundedness: {'✓ Grounded' if groundedness_result['grounded'] else '✗ Hallucinated'}")
    print(f"  {groundedness_result['explanation'][:200]}...")

    return result


async def main():
    """Main evaluation function."""
    parser = argparse.ArgumentParser(description="Evaluate agent responses using LLM-as-a-judge")
    parser.add_argument(
        "--dataset",
        type=str,
        default="scripts/eval_dataset.json",
        help="Path to evaluation dataset JSON file",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Path to save results JSON file (optional)",
    )

    args = parser.parse_args()

    # Resolve dataset path
    script_dir = Path(__file__).parent
    dataset_path = script_dir / args.dataset if not os.path.isabs(args.dataset) else Path(args.dataset)

    if not dataset_path.exists():
        print(f"Error: Dataset file not found: {dataset_path}")
        sys.exit(1)

    # Load dataset
    print(f"Loading dataset from: {dataset_path}")
    dataset = load_dataset(str(dataset_path))
    test_cases = dataset.get("test_cases", [])

    if not test_cases:
        print("Error: No test cases found in dataset")
        sys.exit(1)

    print(f"Loaded {len(test_cases)} test cases\n")

    # Initialize agent
    print("Initializing agent...")
    agent = create_macbook_agent()
    print("Agent initialized\n")

    # Run evaluations
    results = []
    for i, test_case in enumerate(test_cases, 1):
        try:
            result = await evaluate_test_case(agent, test_case, i, len(test_cases))
            results.append(result)
        except Exception as e:
            print(f"\nError evaluating test case {i}: {e}")
            import traceback

            traceback.print_exc()
            results.append(
                {
                    "test_id": test_case.get("id", f"test_{i}"),
                    "question": test_case.get("question", ""),
                    "error": str(e),
                }
            )

    # Aggregate results
    print(f"\n\n{'=' * 80}")
    print("AGGREGATE RESULTS")
    print(f"{'=' * 80}\n")

    successful_results = [r for r in results if "error" not in r]
    if successful_results:
        avg_accuracy = sum(r["evaluations"]["accuracy"]["score"] for r in successful_results) / len(
            successful_results
        )
        avg_utilization = sum(
            r["evaluations"]["utilization"]["score"] for r in successful_results
        ) / len(successful_results)
        avg_utilization_pct = sum(
            r["evaluations"]["utilization"]["percentage_used"] for r in successful_results
        ) / len(successful_results)
        grounded_count = sum(
            1 for r in successful_results if r["evaluations"]["groundedness"]["grounded"]
        )
        grounded_pct = (grounded_count / len(successful_results)) * 100

        print(f"Total test cases: {len(test_cases)}")
        print(f"Successful evaluations: {len(successful_results)}")
        print(f"Failed evaluations: {len(results) - len(successful_results)}")
        print(f"\nAverage Accuracy: {avg_accuracy:.2f}/5")
        print(f"Average Utilization: {avg_utilization:.2f}/5 ({avg_utilization_pct:.1f}%)")
        print(f"Groundedness: {grounded_count}/{len(successful_results)} ({grounded_pct:.1f}%)")

        # Detailed breakdown
        print(f"\n{'─' * 80}")
        print("DETAILED BREAKDOWN:")
        print(f"{'─' * 80}")
        for result in successful_results:
            print(f"\n{result['test_id']}:")
            print(f"  Accuracy: {result['evaluations']['accuracy']['score']}/5")
            print(f"  Utilization: {result['evaluations']['utilization']['score']}/5")
            print(f"  Grounded: {result['evaluations']['groundedness']['grounded']}")

    # Save results if requested
    if args.output:
        output_path = Path(args.output)
        output_data = {
            "summary": {
                "total_tests": len(test_cases),
                "successful": len(successful_results),
                "failed": len(results) - len(successful_results),
                "average_accuracy": avg_accuracy if successful_results else 0,
                "average_utilization": avg_utilization if successful_results else 0,
                "average_utilization_percentage": avg_utilization_pct if successful_results else 0,
                "grounded_count": grounded_count if successful_results else 0,
                "grounded_percentage": grounded_pct if successful_results else 0,
            },
            "results": results,
        }
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        print(f"\nResults saved to: {output_path}")

    print(f"\n{'=' * 80}")
    print("Evaluation complete!")
    print(f"{'=' * 80}\n")


if __name__ == "__main__":
    asyncio.run(main())

