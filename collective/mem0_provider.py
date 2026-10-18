"""Real LangChain tool-call adapter for the explicitly selected provider."""

import json

from mem0.llms.base import LLMBase


class ConfiguredMemoryLLM(LLMBase):
    def __init__(self, config):
        super().__init__(config)
        from .models import chat_model
        from .settings import settings

        self.model = chat_model(max_tokens=config.max_tokens or settings.memory_max_output_tokens,
            output_limit=settings.memory_max_output_tokens)
        self.failures = []

    def generate_response(self, messages, response_format=None, tools=None, tool_choice="auto", **kwargs):
        try:
            return self._generate_response(messages, response_format, tools, tool_choice, **kwargs)
        except Exception as exc:
            # Mem0 catches some provider exceptions internally. Keep a sanitized
            # signal so the outer adapter can reject a partial success response.
            self.failures.append(type(exc).__name__)
            raise

    def _generate_response(self, messages, response_format=None, tools=None, tool_choice="auto", **kwargs):
        model = self.model.bind_tools(tools, tool_choice=tool_choice) if tools else self.model
        if response_format and not tools:
            messages = [
                *messages,
                {"role": "user", "content": "Return a valid JSON object only, without Markdown fences."},
            ]
        result = model.invoke(messages)
        text = (
            result.content
            if isinstance(result.content, str)
            else "".join(block.get("text", "") for block in result.content if isinstance(block, dict))
        )
        if tools:
            return {
                "content": text,
                "tool_calls": [{"name": t["name"], "arguments": t["args"]} for t in result.tool_calls],
            }
        if response_format:
            json.loads(text)  # Fail explicitly on malformed provider output.
        return text
