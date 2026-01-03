import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")


class Config:
    # API Keys
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")

    # Models
    CLAUDE_MODEL: str = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

    # Mode flags
    USE_GEMINI_ONLY: bool = os.getenv("USE_GEMINI_ONLY", "false").lower() == "true"
    USE_CLAUDE_ONLY: bool = os.getenv("USE_CLAUDE_ONLY", "false").lower() == "true"
    SIMPLE_MODE: bool = os.getenv("SIMPLE_MODE", "false").lower() == "true"

    # Paths
    PROJECT_ROOT: Path = Path(__file__).parent
    DATA_DIR: Path = PROJECT_ROOT / "data"

    @classmethod
    def validate(cls) -> None:
        errors = []
        if cls.USE_GEMINI_ONLY and not cls.GOOGLE_API_KEY:
            errors.append("GOOGLE_API_KEY not set")
        elif cls.USE_CLAUDE_ONLY and not cls.ANTHROPIC_API_KEY:
            errors.append("ANTHROPIC_API_KEY not set")
        elif not cls.GOOGLE_API_KEY and not cls.ANTHROPIC_API_KEY:
            errors.append("No API keys set - need GOOGLE_API_KEY or ANTHROPIC_API_KEY")

        if errors:
            raise ValueError(f"Configuration errors: {', '.join(errors)}")

    @classmethod
    def ensure_dirs(cls) -> None:
        """Create necessary directories."""
        cls.DATA_DIR.mkdir(parents=True, exist_ok=True)

    @classmethod
    def print_status(cls) -> str:
        """Return current mode status."""
        if cls.SIMPLE_MODE:
            provider = (
                "Gemini"
                if cls.USE_GEMINI_ONLY
                else "Claude" if cls.USE_CLAUDE_ONLY else "Gemini"
            )
            return f"Simple Mode ({provider})"
        return "Multi-Agent Mode"


Config.validate()
Config.ensure_dirs()
