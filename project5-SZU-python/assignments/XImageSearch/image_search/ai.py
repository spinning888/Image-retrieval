from __future__ import annotations
from django.conf import settings


class ClaudeClientUnavailable(Exception):
    pass


def complete_with_claude(prompt: str, system: str | None = None, temperature: float = 0.2) -> str:
    """
    Minimal wrapper for Anthropic Claude (optional).
    Must NEVER break page rendering if not configured.
    """
    if not getattr(settings, "ENABLE_CLAUDE_SONNET", False):
        raise ClaudeClientUnavailable("Claude is disabled (ENABLE_CLAUDE_SONNET=False)")

    api_key = (getattr(settings, "ANTHROPIC_API_KEY", "") or "").strip()
    if not api_key:
        raise ClaudeClientUnavailable("ANTHROPIC_API_KEY is missing")

    model = (getattr(settings, "CLAUDE_MODEL", "") or "").strip() or "claude-3-5-sonnet-latest"

    try:
        import anthropic  # type: ignore
    except Exception as e:
        raise ClaudeClientUnavailable(f"anthropic package not installed: {e}")

    client = anthropic.Anthropic(api_key=api_key)

    resp = client.messages.create(
        model=model,
        max_tokens=1024,
        temperature=float(temperature),
        system=system or "You are a helpful assistant.",
        messages=[{"role": "user", "content": prompt}],
    )

    parts: list[str] = []
    for block in getattr(resp, "content", []) or []:
        if getattr(block, "type", "") == "text":
            parts.append(getattr(block, "text", "") or "")
    return "\n".join(parts).strip()
