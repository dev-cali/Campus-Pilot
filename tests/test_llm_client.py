"""Patch the OpenAI SDK itself: no live provider calls, even with real env keys."""

import json
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from ai.document_processing import split_document_text
from ai.llm_client import OpenAIAnswerGenerator
from ai.local_retrieval import Evidence


class LlmClientTests(unittest.TestCase):
    def setUp(self):
        chunk = split_document_text("FICTIONAL: imaginary learners review a sample list.",
                                    document_id=1, page_no=1, source_reference="fictional://demo-campus/test",
                                    title="Fictional example", version="v1")[0]
        self.evidence = (Evidence("e1", chunk, ("learners",)),)

    def response(self, *, finish="stop", refusal=None, content='{"status":"insufficient_evidence","selections":[]}'):
        return SimpleNamespace(choices=[SimpleNamespace(finish_reason=finish,
                               message=SimpleNamespace(refusal=refusal, content=content))])

    def test_missing_configuration_never_creates_client(self):
        with patch.dict("os.environ", {}, clear=True), patch("openai.OpenAI") as sdk:
            with self.assertRaisesRegex(RuntimeError, "^provider_not_configured$"):
                OpenAIAnswerGenerator().generate("sample", self.evidence)
            sdk.assert_not_called()

    def test_sdk_request_is_bounded_structured_and_has_no_tools(self):
        with patch.dict("os.environ", {"AI_API_KEY": "fictional-test-value", "AI_MODEL": "mock-model"}), patch("openai.OpenAI") as sdk:
            client = sdk.return_value.__enter__.return_value
            client.chat.completions.create.return_value = self.response()
            raw = OpenAIAnswerGenerator().generate("sample", self.evidence)
            self.assertEqual(json.loads(raw)["status"], "insufficient_evidence")
            self.assertEqual(sdk.call_args.kwargs["timeout"], 20.0)
            self.assertEqual(sdk.call_args.kwargs["max_retries"], 0)
            kwargs = client.chat.completions.create.call_args.kwargs
            self.assertEqual(kwargs["response_format"]["type"], "json_schema")
            self.assertFalse(kwargs["store"])
            self.assertNotIn("tools", kwargs)
            self.assertNotIn("fictional-test-value", json.dumps(kwargs["messages"]))
            self.assertEqual(json.loads(kwargs["messages"][1]["content"])["passages"][0]["evidence_id"], "e1")

    def test_refusal_truncation_and_missing_content_are_rejected(self):
        with patch.dict("os.environ", {"AI_API_KEY": "fictional-test-value", "AI_MODEL": "mock-model"}), patch("openai.OpenAI") as sdk:
            client = sdk.return_value.__enter__.return_value
            for response in (self.response(finish="length"), self.response(refusal="refusal"),
                             self.response(content=None), SimpleNamespace(choices=[])):
                client.chat.completions.create.return_value = response
                with self.assertRaisesRegex(RuntimeError, "^invalid_provider_response$"):
                    OpenAIAnswerGenerator().generate("sample", self.evidence)


if __name__ == "__main__":
    unittest.main()
