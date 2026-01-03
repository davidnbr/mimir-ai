"""
Jarvis Multi-Agent Workflow
Custom supervisor pattern using google-genai SDK directly.
No deprecated LangChain dependencies.
"""
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Generator

from google import genai
from google.genai import types

from config import Config
from memory import MemoryManager
from prompts import (
    JARVIS_SUPERVISOR_PROMPT,
    PROMPT_REFINER_PROMPT,
    BACKEND_AGENT_PROMPT,
    FRONTEND_AGENT_PROMPT,
    DEVOPS_AGENT_PROMPT,
    PR_REVIEWER_PROMPT,
)


class AgentType(Enum):
    """Available agent types."""
    SUPERVISOR = "supervisor"
    PROMPT_REFINER = "prompt_refiner"
    BACKEND = "backend_agent"
    FRONTEND = "frontend_agent"
    DEVOPS = "devops_agent"
    PR_REVIEWER = "pr_reviewer"


@dataclass
class AgentResponse:
    """Response from an agent."""
    agent: AgentType
    content: str
    metadata: dict = field(default_factory=dict)


@dataclass
class WorkflowState:
    """Current state of the workflow."""
    original_query: str
    refined_query: Optional[str] = None
    specialist_response: Optional[str] = None
    review_result: Optional[str] = None
    final_response: Optional[str] = None
    agents_called: list = field(default_factory=list)
    current_agent: Optional[AgentType] = None


class Agent:
    """Base agent class wrapping Gemini API."""
    
    def __init__(
        self,
        agent_type: AgentType,
        system_prompt: str,
        client: genai.Client,
        model: str,
    ):
        self.agent_type = agent_type
        self.system_prompt = system_prompt
        self.client = client
        self.model = model
    
    def invoke(self, message: str, context: Optional[str] = None) -> str:
        """Invoke the agent with a message."""
        full_prompt = self.system_prompt
        if context:
            full_prompt = f"{self.system_prompt}\n\n[Context from previous steps:]\n{context}"
        
        response = self.client.models.generate_content(
            model=self.model,
            contents=[types.Content(role="user", parts=[types.Part(text=message)])],
            config=types.GenerateContentConfig(
                system_instruction=full_prompt,
                max_output_tokens=4096,
            ),
        )
        return response.text
    
    def stream(self, message: str, context: Optional[str] = None) -> Generator[str, None, None]:
        """Stream response from the agent."""
        full_prompt = self.system_prompt
        if context:
            full_prompt = f"{self.system_prompt}\n\n[Context from previous steps:]\n{context}"
        
        for chunk in self.client.models.generate_content_stream(
            model=self.model,
            contents=[types.Content(role="user", parts=[types.Part(text=message)])],
            config=types.GenerateContentConfig(
                system_instruction=full_prompt,
                max_output_tokens=4096,
            ),
        ):
            if chunk.text:
                yield chunk.text


class Supervisor(Agent):
    """
    Supervisor agent that routes to specialized agents.
    Uses function calling to decide which agent to invoke.
    """
    
    ROUTING_PROMPT = """You are the JARVIS supervisor. Analyze the user's request and decide which specialist agent should handle it.

Available agents:
- backend_agent: Python, Go, Node.js, APIs, databases, server-side code
- frontend_agent: React, TypeScript, CSS, HTML, UI/UX, web interfaces
- devops_agent: Terraform, Docker, Kubernetes, CI/CD, AWS, infrastructure, NixOS
- none: General questions that don't need a specialist

Respond with ONLY a JSON object:
{"agent": "<agent_name>", "reason": "<brief reason>"}

Examples:
- "Create a Python API endpoint" -> {"agent": "backend_agent", "reason": "Python API development"}
- "Style this React component" -> {"agent": "frontend_agent", "reason": "React styling"}
- "Set up a Terraform module" -> {"agent": "devops_agent", "reason": "Infrastructure as code"}
- "What time is it?" -> {"agent": "none", "reason": "General question"}
"""
    
    def route(self, query: str) -> Optional[AgentType]:
        """Determine which agent should handle the query."""
        response = self.client.models.generate_content(
            model=self.model,
            contents=[types.Content(role="user", parts=[types.Part(text=query)])],
            config=types.GenerateContentConfig(
                system_instruction=self.ROUTING_PROMPT,
                max_output_tokens=256,
            ),
        )
        
        try:
            # Parse JSON response
            text = response.text.strip()
            # Handle markdown code blocks
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            
            result = json.loads(text)
            agent_name = result.get("agent", "none")
            
            agent_map = {
                "backend_agent": AgentType.BACKEND,
                "frontend_agent": AgentType.FRONTEND,
                "devops_agent": AgentType.DEVOPS,
            }
            
            return agent_map.get(agent_name)
            
        except (json.JSONDecodeError, KeyError):
            # Default to devops for ambiguous cases (given user's background)
            return AgentType.DEVOPS


class MultiAgentWorkflow:
    """
    Orchestrates the multi-agent workflow:
    User -> Prompt Refiner -> Specialist -> PR Reviewer -> User
    """
    
    def __init__(self, session_id: Optional[str] = None):
        self.client = genai.Client(api_key=Config.GOOGLE_API_KEY)
        self.model = Config.GEMINI_MODEL
        self.session_id = session_id or "default"
        
        # Initialize memory
        self.memory = MemoryManager()
        
        # Initialize agents
        self._init_agents()
    
    def _init_agents(self):
        """Initialize all agents."""
        self.supervisor = Supervisor(
            agent_type=AgentType.SUPERVISOR,
            system_prompt=JARVIS_SUPERVISOR_PROMPT,
            client=self.client,
            model=self.model,
        )
        
        self.agents = {
            AgentType.PROMPT_REFINER: Agent(
                agent_type=AgentType.PROMPT_REFINER,
                system_prompt=PROMPT_REFINER_PROMPT,
                client=self.client,
                model=self.model,
            ),
            AgentType.BACKEND: Agent(
                agent_type=AgentType.BACKEND,
                system_prompt=BACKEND_AGENT_PROMPT,
                client=self.client,
                model=self.model,
            ),
            AgentType.FRONTEND: Agent(
                agent_type=AgentType.FRONTEND,
                system_prompt=FRONTEND_AGENT_PROMPT,
                client=self.client,
                model=self.model,
            ),
            AgentType.DEVOPS: Agent(
                agent_type=AgentType.DEVOPS,
                system_prompt=DEVOPS_AGENT_PROMPT,
                client=self.client,
                model=self.model,
            ),
            AgentType.PR_REVIEWER: Agent(
                agent_type=AgentType.PR_REVIEWER,
                system_prompt=PR_REVIEWER_PROMPT,
                client=self.client,
                model=self.model,
            ),
        }
    
    def _get_memory_context(self, query: str) -> str:
        """Retrieve relevant memory context."""
        memories = self.memory.recall(query, n_results=3)
        
        if not memories:
            return ""
        
        context_parts = []
        for mem in memories:
            if mem["relevance"] > 0.5:
                context_parts.append(f"- {mem['content'][:300]}")
        
        if context_parts:
            return "[Relevant past context:]\n" + "\n".join(context_parts)
        return ""
    
    def run(self, query: str, skip_review: bool = False) -> Generator[AgentResponse, None, None]:
        """
        Run the full workflow, yielding responses from each agent.
        
        Args:
            query: User's input
            skip_review: Skip PR review step (faster, fewer API calls)
        
        Yields:
            AgentResponse for each step
        """
        state = WorkflowState(original_query=query)
        memory_context = self._get_memory_context(query)
        
        # Step 1: Route to determine specialist
        target_agent = self.supervisor.route(query)
        
        if target_agent is None:
            # No specialist needed - supervisor handles directly
            response = self.supervisor.invoke(
                query,
                context=memory_context if memory_context else None,
            )
            yield AgentResponse(
                agent=AgentType.SUPERVISOR,
                content=response,
            )
            
            # Store in memory
            self.memory.store(self.session_id, query, response)
            return
        
        # Step 2: Refine the prompt
        yield AgentResponse(
            agent=AgentType.PROMPT_REFINER,
            content="",
            metadata={"status": "starting"},
        )
        
        refiner = self.agents[AgentType.PROMPT_REFINER]
        refined = refiner.invoke(query, context=memory_context if memory_context else None)
        state.refined_query = refined
        state.agents_called.append(AgentType.PROMPT_REFINER)
        
        yield AgentResponse(
            agent=AgentType.PROMPT_REFINER,
            content=refined,
        )
        
        # Step 3: Call specialist
        yield AgentResponse(
            agent=target_agent,
            content="",
            metadata={"status": "starting"},
        )
        
        specialist = self.agents[target_agent]
        specialist_response = specialist.invoke(
            refined,
            context=f"Original request: {query}",
        )
        state.specialist_response = specialist_response
        state.agents_called.append(target_agent)
        
        yield AgentResponse(
            agent=target_agent,
            content=specialist_response,
        )
        
        # Step 4: PR Review (optional)
        if not skip_review:
            yield AgentResponse(
                agent=AgentType.PR_REVIEWER,
                content="",
                metadata={"status": "starting"},
            )
            
            reviewer = self.agents[AgentType.PR_REVIEWER]
            review = reviewer.invoke(
                f"Review this response:\n\n{specialist_response}",
                context=f"Original request: {query}\nRefined request: {refined}",
            )
            state.review_result = review
            state.agents_called.append(AgentType.PR_REVIEWER)
            
            yield AgentResponse(
                agent=AgentType.PR_REVIEWER,
                content=review,
            )
        
        # Step 5: Final summary from supervisor
        final_prompt = f"""Summarize the results for the user in your Jarvis style.

Original request: {query}
Specialist ({target_agent.value}) response: {specialist_response[:1000]}...
{"Review: " + state.review_result[:500] if state.review_result else ""}

Provide a brief, elegant summary. Don't repeat the full code - just confirm what was done and any key points."""
        
        final_response = self.supervisor.invoke(final_prompt)
        state.final_response = final_response
        
        yield AgentResponse(
            agent=AgentType.SUPERVISOR,
            content=final_response,
        )
        
        # Store in memory
        full_response = f"[Agents: {', '.join(a.value for a in state.agents_called)}]\n\n{specialist_response}"
        self.memory.store(self.session_id, query, full_response)
    
    def run_fast(self, query: str) -> Generator[AgentResponse, None, None]:
        """
        Run a faster workflow (skip refiner and reviewer).
        Good for simple questions or when rate limited.
        
        User -> Route -> Speci
