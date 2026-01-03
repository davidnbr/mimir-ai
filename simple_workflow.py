"""
Jarvis Simple Workflow
Single-agent mode with memory integration.
"""

from typing import Optional
from uuid import uuid4

from google import genai
from google.genai import types

from config import Config
from prompts import JARVIS_SIMPLE_PROMPT
from memory import MemoryManager


class SimpleJarvis:
    """
    Simple single-agent Jarvis with persistent memory.
    """

    def __init__(self, session_id: Optional[str] = None):
        self.client = genai.Client(api_key=Config.GOOGLE_API_KEY)
        self.model = Config.GEMINI_MODEL
        self.session_id = session_id or str(uuid4())
        self.history: list[types.Content] = []
        self.system_instruction = JARVIS_SIMPLE_PROMPT

        # Initialize memory
        self.memory = MemoryManager()

        # Load recent history from memory if resuming session
        self._load_session_history()

    def _load_session_history(self):
        """Load conversation history from memory for this session."""
        recent = self.memory.get_recent_history(self.session_id, limit=10)

        for msg in recent:
            role = "user" if msg["role"] == "user" else "model"
            self.history.append(
                types.Content(role=role, parts=[types.Part(text=msg["content"])])
            )

    def _get_relevant_context(self, query: str) -> str:
        """Retrieve relevant memories for the current query."""
        memories = self.memory.recall(query, n_results=3)

        if not memories:
            return ""

        context_parts = ["[Relevant memories from past conversations:]"]
        for mem in memories:
            if mem["relevance"] > 0.5:  # Only include if reasonably relevant
                context_parts.append(f"- {mem['content'][:300]}...")

        if len(context_parts) > 1:
            return "\n".join(context_parts) + "\n\n"
        return ""

    def _detect_patterns(self, message: str):
        """Detect and track patterns in user messages."""
        message_lower = message.lower()

        # Track topic patterns
        topics = {
            "terraform": ["terraform", "tf", "infrastructure", "iac"],
            "python": ["python", "py", "pip", "venv"],
            "docker": ["docker", "container", "dockerfile"],
            "kubernetes": ["kubernetes", "k8s", "kubectl", "helm"],
            "aws": ["aws", "s3", "ec2", "lambda", "cloudformation"],
            "git": ["git", "github", "commit", "branch", "merge"],
            "debugging": ["debug", "error", "fix", "issue", "bug"],
            "architecture": ["architecture", "design", "pattern", "structure"],
        }

        for topic, keywords in topics.items():
            if any(kw in message_lower for kw in keywords):
                self.memory.track_pattern("topic", topic)

        # Track task type patterns
        if any(kw in message_lower for kw in ["create", "write", "generate", "make"]):
            self.memory.track_pattern("task_type", "creation")
        elif any(kw in message_lower for kw in ["fix", "debug", "error", "issue"]):
            self.memory.track_pattern("task_type", "debugging")
        elif any(kw in message_lower for kw in ["explain", "what is", "how does"]):
            self.memory.track_pattern("task_type", "explanation")
        elif any(kw in message_lower for kw in ["review", "check", "validate"]):
            self.memory.track_pattern("task_type", "review")

    def _build_system_prompt(self, query: str) -> str:
        """Build system prompt with memory context."""
        base = self.system_instruction

        # Add relevant memory context
        memory_context = self._get_relevant_context(query)

        # Add pattern insights
        patterns = self.memory.get_patterns(min_frequency=3)
        if patterns:
            top_topics = [
                p["pattern_data"] for p in patterns if p["pattern_type"] == "topic"
            ][:3]
            if top_topics:
                pattern_note = (
                    f"\n\n[Note: User frequently works with: {', '.join(top_topics)}]"
                )
                base += pattern_note

        if memory_context:
            return f"{base}\n\n{memory_context}"
        return base

    def chat(self, message: str) -> str:
        """Send a message and get a response with memory."""
        # Detect patterns
        self._detect_patterns(message)

        # Add user message to history
        self.history.append(
            types.Content(role="user", parts=[types.Part(text=message)])
        )

        # Build context-aware system prompt
        system_prompt = self._build_system_prompt(message)

        # Call model
        response = self.client.models.generate_content(
            model=self.model,
            contents=self.history,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                max_output_tokens=4096,
            ),
        )

        response_text = response.text

        # Add assistant response to history
        self.history.append(
            types.Content(role="model", parts=[types.Part(text=response_text)])
        )

        # Store in persistent memory
        self.memory.store(
            session_id=self.session_id,
            user_message=message,
            assistant_response=response_text,
        )

        # Keep session history manageable
        if len(self.history) > 20:
            self.history = self.history[-20:]

        return response_text

    def stream(self, message: str):
        """Stream a response with memory."""
        # Detect patterns
        self._detect_patterns(message)

        # Add user message to history
        self.history.append(
            types.Content(role="user", parts=[types.Part(text=message)])
        )

        # Build context-aware system prompt
        system_prompt = self._build_system_prompt(message)

        # Stream response
        full_response = ""

        for chunk in self.client.models.generate_content_stream(
            model=self.model,
            contents=self.history,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
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

        # Store in persistent memory
        self.memory.store(
            session_id=self.session_id,
            user_message=message,
            assistant_response=full_response,
        )

        if len(self.history) > 20:
            self.history = self.history[-20:]

    def clear_history(self):
        """Clear session history (memory persists)."""
        self.history = []

    def get_memory_stats(self) -> dict:
        """Get memory statistics."""
        return self.memory.get_stats()

    def get_patterns(self) -> list[dict]:
        """Get detected patterns."""
        return self.memory.get_patterns()

    def close(self):
        """Clean up resources."""
        self.memory.close()
