from types import ModuleType, SimpleNamespace
import sys

# Keep this unit test offline: llm.py only needs the OpenAI symbol at import time.
fake_openai = ModuleType("openai")
fake_openai.OpenAI = object
sys.modules.setdefault("openai", fake_openai)

from orbitalforge import llm


class FakeCompletions:
    def __init__(self):
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        mode = kwargs["response_format"]["type"]
        if mode == "json_schema":
            raise RuntimeError("json_validate_failed")
        message = SimpleNamespace(content='{"summary":"ok","task_complete":false,"operations":[]}')
        usage = SimpleNamespace(prompt_tokens=123, completion_tokens=45)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)], usage=usage)


class FakeClient:
    def __init__(self):
        self.chat = SimpleNamespace(completions=FakeCompletions())


def test_call_json_falls_back_to_json_object(monkeypatch):
    client = FakeClient()
    monkeypatch.setattr(llm, "_client", lambda: client)
    config = SimpleNamespace(max_api_attempts=1)

    def validate(raw):
        assert raw["summary"] == "ok"
        return raw

    parsed, input_tokens, output_tokens = llm._call_json(
        config,
        model="openai/gpt-oss-120b",
        fallback_model="",
        reasoning_effort="high",
        max_output_tokens=500,
        instructions="Return JSON.",
        input_text="Do work.",
        schema_name="work",
        schema=llm.WORK_SCHEMA,
        validate=validate,
    )

    assert parsed["summary"] == "ok"
    assert (input_tokens, output_tokens) == (123, 45)
    assert [c["response_format"]["type"] for c in client.chat.completions.calls] == [
        "json_schema",
        "json_object",
    ]
    assert all(c["extra_body"]["reasoning_format"] == "hidden" for c in client.chat.completions.calls)


def test_usage_supports_responses_and_chat_shapes():
    chat = SimpleNamespace(usage=SimpleNamespace(prompt_tokens=10, completion_tokens=20))
    responses = SimpleNamespace(usage=SimpleNamespace(input_tokens=30, output_tokens=40))
    assert llm._usage(chat) == (10, 20)
    assert llm._usage(responses) == (30, 40)
