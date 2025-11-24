"""LLM-as-a-judge evaluators for agent responses."""

import os
from typing import Annotated, TypedDict

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

# Load environment variables
load_dotenv()

# Initialize judge LLM
judge_llm = ChatOpenAI(
    model="gpt-4o",
    temperature=0,
    api_key=os.getenv("OPENAI_API_KEY"),
)


# Accuracy evaluation schema
class AccuracyGrade(TypedDict):
    """Schema for accuracy evaluation output."""

    explanation: Annotated[str, ..., "Explain your reasoning for the score"]
    score: Annotated[int, ..., "Score from 1-5"]


accuracy_instructions = """You are evaluating an AI assistant's response accuracy.
Given the QUESTION, RETRIEVED CONTEXT (tool results), and ASSISTANT RESPONSE, score the accuracy:

Scoring criteria:
- 5: Completely accurate, all facts match retrieved context perfectly
- 4: Mostly accurate, minor discrepancies or missing details
- 3: Partially accurate, some facts are correct but others are unsupported or incorrect
- 2: Mostly inaccurate, most facts don't match the retrieved context
- 1: Completely inaccurate or fabricated information

Consider:
1. Whether the facts stated in the response are supported by the retrieved context
2. Whether the response contains any incorrect information
3. Whether the response omits important information from the context
4. Whether the response adds unsupported claims

Provide a clear explanation of your reasoning before assigning the score."""


def accuracy_evaluator(
    test_case: dict, agent_output: dict, tool_context: list[dict]
) -> dict:
    """
    Evaluate the accuracy of the agent's response based on retrieved information.

    Args:
        test_case: Test case with question and optional reference_answer
        agent_output: Agent's response output
        tool_context: List of tool calls with inputs and results

    Returns:
        Dictionary with score, explanation, and key
    """
    question = test_case.get("question", "")
    response = agent_output.get("output", "")
    reference_answer = test_case.get("reference_answer", "")

    # Format tool context for the judge
    context_parts = []
    for tool_call in tool_context:
        tool_name = tool_call.get("tool_name", "unknown")
        tool_input = tool_call.get("input", {})
        tool_result = tool_call.get("result", "")
        context_parts.append(
            f"Tool: {tool_name}\nInput: {tool_input}\nResult: {tool_result[:1000]}"
        )

    retrieved_context = "\n\n".join(context_parts) if context_parts else "No tools were called."

    # Build prompt for judge
    prompt = f"""QUESTION: {question}

RETRIEVED CONTEXT (from tools):
{retrieved_context}

ASSISTANT RESPONSE:
{response}"""

    if reference_answer:
        prompt += f"\n\nREFERENCE ANSWER (for comparison):\n{reference_answer}"

    # Get structured evaluation
    grader = judge_llm.with_structured_output(AccuracyGrade, method="json_schema", strict=True)
    grade = grader.invoke(
        [
            {"role": "system", "content": accuracy_instructions},
            {"role": "user", "content": prompt},
        ]
    )

    return {
        "key": "accuracy",
        "score": grade["score"],
        "explanation": grade["explanation"],
    }


# Information utilization evaluation schema
class UtilizationGrade(TypedDict):
    """Schema for information utilization evaluation output."""

    explanation: Annotated[str, ..., "Explain your reasoning for the score"]
    score: Annotated[int, ..., "Score from 1-5"]
    percentage_used: Annotated[float, ..., "Estimated percentage of retrieved info used (0-100)"]


utilization_instructions = """You are evaluating how much of the retrieved information was actually used in the assistant's response.

Given the RETRIEVED CONTEXT (tool results) and ASSISTANT RESPONSE, score the information utilization:

Scoring criteria:
- 5: Excellent utilization - most or all relevant retrieved information is incorporated
- 4: Good utilization - significant portion of retrieved information is used
- 3: Moderate utilization - some retrieved information is used, but important details are missed
- 2: Poor utilization - only a small portion of retrieved information is used
- 1: Very poor utilization - almost no retrieved information is used despite being available

Consider:
1. What percentage of the retrieved information appears in the response
2. Whether important details from the context are included
3. Whether the response could have been more comprehensive using the available context
4. Whether the response adds information not in the context (which is fine, but doesn't count as utilization)

Provide a clear explanation and estimate the percentage of retrieved information that was used."""


def utilization_evaluator(
    test_case: dict, agent_output: dict, tool_context: list[dict]
) -> dict:
    """
    Evaluate how much of the retrieved information was actually used in the response.

    Args:
        test_case: Test case with question
        agent_output: Agent's response output
        tool_context: List of tool calls with inputs and results

    Returns:
        Dictionary with score, explanation, percentage_used, and key
    """
    question = test_case.get("question", "")
    response = agent_output.get("output", "")

    # Format tool context for the judge
    context_parts = []
    for tool_call in tool_context:
        tool_name = tool_call.get("tool_name", "unknown")
        tool_input = tool_call.get("input", {})
        tool_result = tool_call.get("result", "")
        context_parts.append(
            f"Tool: {tool_name}\nInput: {tool_input}\nResult: {tool_result[:1000]}"
        )

    retrieved_context = "\n\n".join(context_parts) if context_parts else "No tools were called."

    # Build prompt for judge
    prompt = f"""QUESTION: {question}

RETRIEVED CONTEXT (from tools):
{retrieved_context}

ASSISTANT RESPONSE:
{response}"""

    # Get structured evaluation
    grader = judge_llm.with_structured_output(UtilizationGrade, method="json_schema", strict=True)
    grade = grader.invoke(
        [
            {"role": "system", "content": utilization_instructions},
            {"role": "user", "content": prompt},
        ]
    )

    return {
        "key": "utilization",
        "score": grade["score"],
        "explanation": grade["explanation"],
        "percentage_used": grade["percentage_used"],
    }


# Groundedness evaluation schema
class GroundednessGrade(TypedDict):
    """Schema for groundedness evaluation output."""

    explanation: Annotated[str, ..., "Explain your reasoning for the score"]
    grounded: Annotated[bool, ..., "True if response is grounded in retrieved context, False if hallucinated"]


groundedness_instructions = """You are evaluating whether the assistant's response is grounded in the retrieved context or contains hallucinations.

Given the RETRIEVED CONTEXT (tool results) and ASSISTANT RESPONSE, determine if the response is grounded:

A grounded response:
- Contains only information that can be found in or reasonably inferred from the retrieved context
- Does not make up facts that aren't in the context
- May add reasonable interpretations or connections, but doesn't fabricate details

A hallucinated response:
- Contains specific facts, numbers, or claims that cannot be found in the retrieved context
- Makes up information that contradicts the context
- States information as fact when it's not in the context

Note: It's acceptable for the response to:
- Summarize or rephrase information from the context
- Make reasonable inferences based on the context
- Add general knowledge that doesn't contradict the context
- Structure the information differently than in the context

But it's NOT acceptable to:
- Invent specific numbers, dates, or facts not in the context
- Make claims that directly contradict the retrieved context
- State information as fact when it's not supported by the context

Provide a clear explanation of your reasoning."""


def groundedness_evaluator(
    test_case: dict, agent_output: dict, tool_context: list[dict]
) -> dict:
    """
    Evaluate whether the response is grounded in retrieved facts (no hallucination).

    Args:
        test_case: Test case with question
        agent_output: Agent's response output
        tool_context: List of tool calls with inputs and results

    Returns:
        Dictionary with grounded (bool), explanation, and key
    """
    question = test_case.get("question", "")
    response = agent_output.get("output", "")

    # Format tool context for the judge
    context_parts = []
    for tool_call in tool_context:
        tool_name = tool_call.get("tool_name", "unknown")
        tool_input = tool_call.get("input", {})
        tool_result = tool_call.get("result", "")
        context_parts.append(
            f"Tool: {tool_name}\nInput: {tool_input}\nResult: {tool_result[:1000]}"
        )

    retrieved_context = "\n\n".join(context_parts) if context_parts else "No tools were called."

    # Build prompt for judge
    prompt = f"""QUESTION: {question}

RETRIEVED CONTEXT (from tools):
{retrieved_context}

ASSISTANT RESPONSE:
{response}"""

    # Get structured evaluation
    grader = judge_llm.with_structured_output(GroundednessGrade, method="json_schema", strict=True)
    grade = grader.invoke(
        [
            {"role": "system", "content": groundedness_instructions},
            {"role": "user", "content": prompt},
        ]
    )

    return {
        "key": "groundedness",
        "grounded": grade["grounded"],
        "score": 1 if grade["grounded"] else 0,  # Binary score for consistency
        "explanation": grade["explanation"],
    }

