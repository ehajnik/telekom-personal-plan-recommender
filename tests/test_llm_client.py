"""LiteLLM client behaviour with a mocked ``litellm.completion``."""

from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from telekom_profiler.llm import client


def _response(content: str, finish_reason: str = "stop") -> SimpleNamespace:
    message = SimpleNamespace(content=content)
    return SimpleNamespace(choices=[SimpleNamespace(message=message, finish_reason=finish_reason)])


class ChatCompletionTests(unittest.TestCase):
    def setUp(self) -> None:
        patcher = patch.object(client, "llm_enabled", return_value=True)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_retry_budget_exceeds_first_attempt(self) -> None:
        self.assertGreater(client._retry_token_budget(), client.OLLAMA_NUM_PREDICT)

    @patch("litellm.completion")
    def test_truncated_answer_retried_with_larger_budget(self, completion) -> None:
        completion.side_effect = [_response("partial", "length"), _response("full answer")]
        result = client.chat_completion("prompt", model="ollama/qwen2.5:7b")
        self.assertEqual(result, "full answer")
        first, second = (c.kwargs for c in completion.call_args_list)
        self.assertGreater(second["max_tokens"], first["max_tokens"])

    @patch("litellm.completion")
    def test_anthropic_requests_omit_temperature(self, completion) -> None:
        completion.return_value = _response("ok")
        client.chat_completion("prompt", model="anthropic/claude-opus-5-5")
        self.assertNotIn("temperature", completion.call_args.kwargs)

    @patch("litellm.completion")
    def test_ollama_requests_keep_temperature_and_host(self, completion) -> None:
        completion.return_value = _response("ok")
        client.chat_completion("prompt", model="ollama/qwen2.5:7b")
        kwargs = completion.call_args.kwargs
        self.assertEqual(kwargs["temperature"], 0.3)
        self.assertEqual(kwargs["api_base"], client.OLLAMA_HOST)

    @patch("litellm.completion")
    def test_missing_headings_trigger_repair(self, completion) -> None:
        completion.side_effect = [_response("### 1. A"), _response("### 1. A\n### 2. B")]
        result = client.chat_completion(
            "prompt", model="ollama/qwen2.5:7b", required_headings=("### 1. A", "### 2. B")
        )
        self.assertIn("### 2. B", result)


if __name__ == "__main__":
    unittest.main()
