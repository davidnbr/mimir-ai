"""
Jarvis Agent Definitions
Creates specialized agents using LangGraph's create_react_agent.
"""

from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent

from config import Config
from prompts import (
    PROMPT_REFINER_PROMPT,
    BACKEND_AGENT_PROMPT,
    FRONTEND_AGENT_PROMPT,
    DEVOPS_AGENT_PROMPT,
    PR_REVIEWER_PROMPT,
)


def get_claude_model() -> ChatAnthropic:
    """Get Claude model instance."""
    return ChatAnthropic(
        model=Config.CLAUDE_MODEL,
        api_key=Config.ANTHROPIC_API_KEY,
        max_tokens=4096,
    )


def get_coding_model():
    """Get model for coding agents - Claude or Gemini based on config."""
    if getattr(Config, "USE_GEMINI_ONLY", False):
        return get_gemini_model()
    return get_claude_model()


def get_gemini_model() -> ChatGoogleGenerativeAI:
    """Get Gemini model instance."""
    return ChatGoogleGenerativeAI(
        model=Config.GEMINI_MODEL,
        google_api_key=Config.GOOGLE_API_KEY,
        max_output_tokens=4096,
        max_retries=5,
        timeout=120,
    )


def create_prompt_refiner():
    """Create the prompt refinement agent (Gemini)."""
    return create_react_agent(
        model=get_gemini_model(),
        tools=[],  # No tools needed - pure reasoning
        name="prompt_refiner",
        prompt=PROMPT_REFINER_PROMPT,
    )


def create_backend_agent():
    """Create the backend development agent (Claude)."""
    return create_react_agent(
        model=get_coding_model(),
        tools=[],  # Phase 1: No tools. Later: file read/write, shell exec
        name="backend_agent",
        prompt=BACKEND_AGENT_PROMPT,
    )


def create_frontend_agent():
    """Create the frontend development agent (Claude)."""
    return create_react_agent(
        model=get_coding_model(),
        tools=[],
        name="frontend_agent",
        prompt=FRONTEND_AGENT_PROMPT,
    )


def create_devops_agent():
    """Create the DevOps/infrastructure agent (Claude)."""
    return create_react_agent(
        model=get_coding_model(),
        tools=[],
        name="devops_agent",
        prompt=DEVOPS_AGENT_PROMPT,
    )


def create_pr_reviewer():
    """Create the PR review agent (Gemini)."""
    return create_react_agent(
        model=get_gemini_model(),
        tools=[],
        name="pr_reviewer",
        prompt=PR_REVIEWER_PROMPT,
    )


def create_all_agents() -> list:
    """Create all specialized agents."""
    return [
        create_prompt_refiner(),
        create_backend_agent(),
        create_frontend_agent(),
        create_devops_agent(),
        create_pr_reviewer(),
    ]
