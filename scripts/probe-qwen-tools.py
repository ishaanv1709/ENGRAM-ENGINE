"""Measure actual long tool-argument fidelity on the selected model."""
import asyncio
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from collective.models import chat_model


async def main():
    model = chat_model(max_tokens=1000)
    model.include_response_headers = True
    expected = "0123456789" * 80
    result = await model.bind_tools([{"type": "function", "function": {"name": "capture_text", "description": "Capture the supplied text verbatim without shortening it.", "parameters": {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]}}}], tool_choice="capture_text").ainvoke("Call capture_text with the EXACT complete text below, no shortening:\n" + expected)
    received = result.tool_calls[0]["args"]["text"] if result.tool_calls else ""
    report = {"expected_characters": len(expected), "actual_characters": len(received), "exact_match": received == expected,
        "finish_reason": result.response_metadata.get("finish_reason"), "usage": result.usage_metadata,
        "limits": {key: value for key, value in result.response_metadata.get("headers", {}).items() if key.startswith("x-ratelimit-")}}
    Path("data/collective/qwen-tool-fidelity.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report), flush=True)


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
