"""Explicit provider selection shared by DeepAgents and memory extraction."""

from .settings import DependencyUnavailable, require_key, settings


def chat_model(*, max_tokens=6000, output_limit=None):
    if settings.agent_provider == "unconfigured":
        raise DependencyUnavailable("Add your own provider key and model in Profile & settings. No host key is used.")
    if settings.agent_provider == "groq":
        from .model_budget import BudgetedChatOpenAI

        reasoning = {}
        if settings.agent_model.startswith("qwen/"):
            reasoning["reasoning_effort"] = "none"
        elif "gpt-oss" in settings.agent_model:
            reasoning["reasoning_effort"] = "low"
        return BudgetedChatOpenAI(
            model=settings.agent_model,
            api_key=require_key("GROQ_API_KEY", settings.groq_api_key),
            base_url="https://api.groq.com/openai/v1",
            max_tokens=min(max_tokens, output_limit or settings.groq_max_output_tokens),
            **reasoning,
            max_retries=3,
            timeout=90,
            temperature=0,
            model_kwargs={"parallel_tool_calls": False},
        )
    if settings.agent_provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(
            model=settings.agent_model,
            api_key=require_key("ANTHROPIC_API_KEY", settings.anthropic_api_key),
            max_tokens=max_tokens,
            max_retries=0,
            timeout=90,
            temperature=0,
        )
    if settings.agent_api_key:
        from langchain_anthropic import ChatAnthropic
        from langchain_openai import ChatOpenAI

        common = {
            "model": settings.agent_model,
            "api_key": settings.agent_api_key,
            "base_url": settings.agent_base_url,
            "max_tokens": min(max_tokens, output_limit or 4000),
            "max_retries": 0,
            "timeout": 90,
        }
        if settings.agent_protocol == "anthropic":
            return ChatAnthropic(**common)
        extra = (
            {"extra_body": {"provider": {"allow_fallbacks": False}}} if settings.agent_provider == "openrouter" else {}
        )
        return ChatOpenAI(**common, use_responses_api=settings.agent_protocol == "responses", **extra)
    raise DependencyUnavailable("Unsupported AGENT_PROVIDER")
