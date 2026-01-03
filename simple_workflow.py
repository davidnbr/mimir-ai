"""
Jarvis Simple Workflow
Single-agent mode using google-genai SDK directly.
"""

from google import genai
from google.genai import types

from config import Config
from prompts import JARVIS_SIMPLE_PROMPT


class SimpleJarvis:
    """
    Simple single-agent Jarvis using Gemini directly.
    No LangChain overhead, no deprecated packages.
    """

    def __init__(self):
        self.client = genai.Client(api_key=Config.GOOGLE_API_KEY)
        self.model = Config.GEMINI_MODEL
        self.history: list[types.Content] = []
        self.system_instruction = JARVIS_SIMPLE_PROMPT

    def chat(self, message: str) -> str:
        """
        Send a message and get a response.
        Maintains conversation history within session.
        """
        # Add user message to history
        self.history.append(
            types.Content(role="user", parts=[types.Part(text=message)])
        )

        # Call model
        response = self.client.models.generate_content(
            model=self.model,
            contents=self.history,
            config=types.GenerateContentConfig(
                system_instruction=self.system_instruction,
                max_output_tokens=4096,
            ),
        )

        # Extract response text
        response_text = response.text

        # Add assistant response to history
        self.history.append(
            types.Content(role="model", parts=[types.Part(text=response_text)])
        )

        # Keep history manageable (last 10 exchanges = 20 messages)
        if len(self.history) > 20:
            self.history = self.history[-20:]

        return response_text

    def stream(self, message: str):
        """
        Stream a response token by token.
        """
        # Add user message to history
        self.history.append(
            types.Content(role="user", parts=[types.Part(text=message)])
        )

        # Stream response
        full_response = ""

        for chunk in self.client.models.generate_content_stream(
            model=self.model,
            contents=self.history,
            config=types.GenerateContentConfig(
                system_instruction=self.system_instruction,
                max_output_tokens=4096,
            ),
        ):
            if chunk.text:
                full_response += chunk.text
                yield chunk.text

        # Add complete response to history
        self.history.append(
            types.Content(role="model", parts=[types.Part(text=full_response)])
        )

        if len(self.history) > 20:
            self.history = self.history[-20:]

    def clear_history(self):
        """Clear conversation history."""
        self.history = []
