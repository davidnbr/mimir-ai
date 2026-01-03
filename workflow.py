"""
Jarvis Multi-Agent Workflow
Implements the supervisor pattern using LangGraph.
"""

from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph_supervisor import create_supervisor
from langgraph.checkpoint.memory import MemorySaver

from config import Config
from prompts import JARVIS_SUPERVISOR_PROMPT
from agents import create_all_agents


def create_jarvis_workflow(with_memory: bool = True):
    """
    Create the Jarvis multi-agent workflow.

    Args:
        with_memory: Enable conversation memory (checkpointing)

    Returns:
        Compiled LangGraph workflow
    """
    # Create all specialized agents
    agents = create_all_agents()

    # Supervisor uses Gemini for fast routing decisions
    supervisor_model = ChatGoogleGenerativeAI(
        model=Config.GEMINI_MODEL,
        google_api_key=Config.GOOGLE_API_KEY,
        max_output_tokens=2048,
    )

    # Create supervisor workflow
    workflow = create_supervisor(
        agents=agents,
        model=supervisor_model,
        prompt=JARVIS_SUPERVISOR_PROMPT,
        # Keep full history for context
        output_mode="full_history",
    )

    # Compile with optional memory
    if with_memory:
        checkpointer = MemorySaver()
        app = workflow.compile(checkpointer=checkpointer)
    else:
        app = workflow.compile()

    return app


def invoke_jarvis(
    message: str,
    thread_id: str = "default",
    workflow=None,
) -> dict:
    """
    Send a message to Jarvis and get a response.

    Args:
        message: User's input message
        thread_id: Conversation thread ID for memory
        workflow: Pre-compiled workflow (optional, creates new if None)

    Returns:
        Dict with 'messages' containing the conversation
    """
    if workflow is None:
        workflow = create_jarvis_workflow()

    config = {"configurable": {"thread_id": thread_id}}

    result = workflow.invoke(
        {"messages": [{"role": "user", "content": message}]},
        config=config,
    )

    return result


def stream_jarvis(
    message: str,
    thread_id: str = "default",
    workflow=None,
):
    """
    Stream responses from Jarvis.

    Yields events as they happen for real-time output.
    """
    if workflow is None:
        workflow = create_jarvis_workflow()

    config = {"configurable": {"thread_id": thread_id}}

    for event in workflow.stream(
        {"messages": [{"role": "user", "content": message}]},
        config=config,
        stream_mode="updates",
    ):
        yield event
