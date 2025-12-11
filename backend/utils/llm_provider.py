import os
import openai
import httpx
from .langfuse_client import track_event
import time

# Keys
OPENAI_KEY = os.getenv('OPENAI_API_KEY')
CLAUDE_KEY = os.getenv('CLAUDE_API_KEY')

openai.api_key = OPENAI_KEY

# Default model — can be overridden with the env var `DEFAULT_LLM_MODEL`.
# To enable Claude Haiku 4.5 for all clients set `DEFAULT_LLM_MODEL=claude-haiku-4.5`
DEFAULT_LLM_MODEL = os.getenv('DEFAULT_LLM_MODEL', 'claude-haiku-4.5')


def get_default_model() -> str:
    """Return the configured default LLM model name."""
    return DEFAULT_LLM_MODEL


def call_llm(prompt: str, model: str | None = None, max_tokens: int = 512) -> str:
    """Call the configured model and return a text completion.

    Behavior:
    - If the `model` name contains 'claude', attempt to call Anthropic's HTTP API using
      the `CLAUDE_API_KEY` environment variable.
    - Otherwise, fall back to OpenAI's completion/chat API (if `OPENAI_API_KEY` is set).

    Note: This is a small router convenience for the demo environment. In production,
    you may want a more robust client, retries, timeouts, streaming, and proper error handling.
    """
    use_model = model or get_default_model()

    if 'claude' in use_model.lower():
        if not CLAUDE_KEY:
            raise RuntimeError('CLAUDE_API_KEY not set — cannot call Claude model')

        # Typical Anthropic-style endpoint (may vary by provider / account), using a simple complete call.
        url = 'https://api.anthropic.com/v1/complete'
        headers = {
            'Authorization': f'Bearer {CLAUDE_KEY}',
            'Content-Type': 'application/json'
        }
        data = {
            'model': use_model,
            'prompt': prompt,
            'max_tokens_to_sample': max_tokens,
            'temperature': 0.0,
        }

        start = time.time()
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(url, json=data, headers=headers)
            resp.raise_for_status()
            j = resp.json()

        # Anthropic responses historically put the text in 'completion', but APIs vary.
        out = j.get('completion') or j.get('output') or j.get('text') or ''
        try:
            track_event('llm.call', {
                'provider': 'claude',
                'model': use_model,
                'prompt_len': len(prompt),
                'max_tokens': max_tokens,
                'duration_ms': int((time.time() - start) * 1000)
            })
        except Exception:
            pass
        return out

    # Fallback to OpenAI (chat/completions) if OpenAI key is available
    if not OPENAI_KEY:
        raise RuntimeError('No API key configured for OpenAI or Anthropic')

    # Use a simple completion call via the OpenAI SDK as a fallback.
    try:
        start = time.time()
        completion = openai.Completion.create(
            model=use_model,
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=0.0,
        )
        # completion.choices[0].text is the typical field
        out = completion.choices[0].text if completion.choices else ''
        try:
            track_event('llm.call', {
                'provider': 'openai.completion',
                'model': use_model,
                'prompt_len': len(prompt),
                'max_tokens': max_tokens,
                'duration_ms': int((time.time() - start) * 1000)
            })
        except Exception:
            pass
        return out
    except Exception:
        # Try chat completion shape if older/newer API is used
        start = time.time()
        chat = openai.ChatCompletion.create(
            model=use_model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=0.0,
        )
        out = chat.choices[0].message.content if chat.choices else ''
        try:
            track_event('llm.call', {
                'provider': 'openai.chat',
                'model': use_model,
                'prompt_len': len(prompt),
                'max_tokens': max_tokens,
                'duration_ms': int((time.time() - start) * 1000)
            })
        except Exception:
            pass
        return out


def embed_text(text: str) -> list[float]:
    """Placeholder embedding function.

    In production plug in your preferred embedding provider. Left as a small wrapper
    so the rest of the codebase can continue calling `embed_text(...)`.
    """
    # For now return a fixed-length zero-vector to preserve API shape.
    try:
        track_event('llm.embed', {'text_len': len(text)})
    except Exception:
        pass
    return [0.0] * 1536
