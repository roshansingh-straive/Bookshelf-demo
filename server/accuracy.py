"""Accuracy policy derived from the benchmark, not from the answer key."""
import os
from dataclasses import asdict, dataclass

BENCHMARK_URL = "https://atharva-729.github.io/bookshelf-benchmark/"
TILE_EDGE = 1400
OVERLAP = 0.20
MAX_TILES = 48


@dataclass(frozen=True)
class ModelProfile:
    provider: str
    model_id: str
    name: str
    effort: str
    reason: str


OPUS = ModelProfile(
    "anthropic", "claude-opus-5-5", "Claude Opus 5.5", "high",
    "Strongest overall setup in the report; preferred for medium and crowded shelves.",
)
FLASH = ModelProfile(
    "gemini", "gemini-3.8-flash", "Gemini 3.8 Flash", "high",
    "Extended thinking had the highest pooled easy-shelf F1 in both benchmark runs.",
)


def configured_providers():
    return {
        "anthropic": bool(os.environ.get("ANTHROPIC_API_KEY")),
        "gemini": bool(os.environ.get("GEMINI_API_KEY")),
    }


def select_profile(difficulty: str, policy: str = "auto", *, live: bool = False):
    profile = FLASH if policy == "auto" and difficulty == "easy" else OPUS
    if live and not configured_providers()[profile.provider]:
        # Opus is a strong measured alternative for tidy shelves. Never silently
        # substitute the poorly performing crowded-shelf Flash setup for Opus.
        if profile == FLASH and configured_providers()["anthropic"]:
            return ModelProfile(**{**asdict(OPUS), "reason": "Gemini is unavailable; using the report's strongest overall model at high effort."})
        variable = "ANTHROPIC_API_KEY" if profile.provider == "anthropic" else "GEMINI_API_KEY (or ANTHROPIC_API_KEY)"
        raise ValueError(f"Live scanning needs {variable} configured on the server. Replay remains available.")
    return profile
