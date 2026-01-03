"""
Jarvis Simple Workflow
Single-agent mode for lower API usage.
"""

from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from config import Config
from prompts import JARVIS_SIMPLE_PROMPT


def get_model():
    """Get the configured model."""
    if Config.USE_CLAUDE_ONLY:
        return ChatAnthropic(
            model=Config.CLAUDE_MODEL,
            api_key=Config.ANTHROPIC_API_KEY,
            max_tokens=4096,
        )
    # Default to Gemini (including USE_GEMINI_ONLY)
    return ChatGoogleGenerativeAI(
        model=Config.GEMINI_MODEL,
        google_api_key=Config.GOOGLE_API_KEY,
        max_output_tokens=4096,
        max_retries=3,
    )


class SimpleJarvis:
    """
    Simple single-agent Jarvis.
    No supervisor, no routing - just direct LLM calls.
    """

    def __init__(self):
        self.model = get_model()
        self.system_message = SystemMessage(content=JARVIS_SIMPLE_PROMPT)
        self.history: list = []

    def chat(self, message: str) -> str:
        """
        Send a message and get a response.
        Maintains conversation history within session.
        """
        # Build messages
        messages = (
            [self.system_message] + self.history + [HumanMessage(content=message)]
        )

        # Call model
        response = self.model.invoke(messages)

        # Update history
        self.history.append(HumanMessage(content=message))
        self.history.append(AIMessage(content=response.content))

        # Keep history manageable (last 10 exchanges)
        if len(self.history) > 20:
            self.history = self.history[-20:]

        return response.content

    def stream(self, message: str):
        """
        Stream a response token by token.
        """
        messages = (
            [self.system_message] + self.history + [HumanMessage(content=message)]
        )

        full_response = ""
        for chunk in self.model.stream(messages):
            if hasattr(chunk, "content") and chunk.content:
                full_response += chunk.content
                yield chunk.content

        # Update history after streaming completes
        self.history.append(HumanMessage(content=message))
        self.history.append(AIMessage(content=full_response))

        if len(self.history) > 20:
            self.history = self.history[-20:]

    def clear_history(self):
        """Clear conversation history."""
        self.history = []
