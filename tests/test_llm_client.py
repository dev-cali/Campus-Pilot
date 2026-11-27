"""Patch the OpenAI SDK itself: no live provider calls, even with real env keys."""

import json
import unittest
import httpx
import httpx2
from openai import BadRequestError
from openai import OpenAI
from types import SimpleNamespace
from unittest.mock import Mock, patch

from ai.document_processing import split_document_text
from ai.llm_client import (DiagnosticFailure, OpenAIAnswerGenerator, classify_rejection,
                           configuration_diagnostics, structured_error_states,
                           provider_response_diagnostics, diagnostic_request)
from ai.local_retrieval import Evidence
from ai.answer_service import AnswerService
from ai.demo_api import create_app
from fastapi.testclient import TestClient
from datetime import date


class LlmClientTests(unittest.TestCase):
    def test_configuration_is_offline_and_sanitized(self):
        cases = (("https://api.openai.com/v1/", True),
                 ("https://api.openai.com.evil.invalid/v1/", False),
                 ("https://user:DO_NOT_LOG@api.openai.com/v1/", False),
                 ("https://api.openai.com/v1/?key=DO_NOT_LOG", False))
        for endpoint, official in cases:
            with patch.dict("os.environ", {"AI_MODEL": "gpt-5-mini", "OPENAI_BASE_URL": endpoint}, clear=True), \
                    patch("openai.OpenAI") as sdk, patch("openai.__version__", "3.37.0"):
                sdk.return_value.base_url = endpoint
                result = configuration_diagnostics()
                self.assertEqual(result, {"model_matches_expected": True, "endpoint_override_exists": True,
                    "official_endpoint": official, "endpoint_check_succeeded": True, "sdk_version": "3.37.0"})
                sdk.return_value.chat.completions.create.assert_not_called()
                sdk.return_value.close.assert_called_once()
                self.assertNotIn("DO_NOT_LOG", json.dumps(result))

    def test_configuration_failure_does_not_leak(self):
        with patch.dict("os.environ", {}, clear=True), patch("openai.OpenAI", side_effect=ValueError("DO_NOT_LOG")), \
                patch("openai.__version__", "DO_NOT_LOG"):
            result = configuration_diagnostics()
            self.assertFalse(result["model_matches_expected"])
            self.assertFalse(result["endpoint_override_exists"])
            self.assertFalse(result["endpoint_check_succeeded"])
            self.assertEqual(result["sdk_version"], "unknown")
            self.assertNotIn("DO_NOT_LOG", json.dumps(result))

    def test_structured_attribute_states(self):
        self.assertEqual(structured_error_states(SimpleNamespace()), dict.fromkeys(("code", "param", "type"), "missing"))
        self.assertEqual(structured_error_states(SimpleNamespace(code=None, param=[], type="DO_NOT_LOG")),
                         {"code": "null", "param": "unrecognized", "type": "unrecognized"})
        self.assertEqual(structured_error_states(SimpleNamespace(code="unsupported_value", param="model", type="invalid_request_error")),
                         dict.fromkeys(("code", "param", "type"), "recognized"))

    def assert_rejection_diagnostics(self, code=None, param=None, *, missing=False,
                                     message="DO_NOT_LOG_BODY", kind=None,
                                     response_headers=None, empty_body=False,
                                     expected_content_type="json",
                                     expected_request_id_present=False,
                                     expected_server_header_present=False,
                                     expected_via_header_present=False):
        body = {"code": code, "param": param, "message": message, "type": kind}
        headers = ({"Content-Type": "application/json"}
                   if response_headers is None else response_headers)
        response_content = b"" if empty_body else json.dumps(body)
        error = BadRequestError(
            "DO_NOT_LOG_MESSAGE", response=httpx.Response(400, request=httpx.Request(
                "POST", "https://example.invalid/DO_NOT_LOG_PATH",
                headers={"Authorization": "DO_NOT_LOG_HEADER"}),
                headers=headers, content=response_content), body=None if empty_body else body)
        if missing:
            del error.code
            del error.param
        retriever = Mock()
        retriever.retrieve.return_value = self.evidence
        service = AnswerService(retriever, OpenAIAnswerGenerator())
        with patch.dict("os.environ", {"AI_API_KEY": "DO_NOT_LOG_KEY", "AI_MODEL": "gpt-5-mini"}), \
                patch("openai.OpenAI") as sdk, \
                self.assertLogs("uvicorn.error", level="WARNING") as captured, \
                TestClient(create_app(service, reference_date=date(2026, 10, 26), require_auth=False)) as api:
            client = sdk.return_value
            client.chat.completions.create.side_effect = error
            response = api.post("/api/ai/ask", json={"question": "DO_NOT_LOG_QUESTION"})
        self.assertEqual(response.status_code, 503)
        body = response.json()
        self.assertEqual(set(body), {"status", "answer", "citations", "fictional"})
        self.assertEqual(body["status"], "unavailable")
        self.assertEqual(body["citations"], [])
        self.assertTrue(body["fictional"])
        self.assertEqual(len(captured.records), 2)
        started, rejected = [json.loads(record.getMessage()) for record in captured.records]
        self.assertEqual(started["category"], "provider_request_started")
        self.assertEqual(rejected["category"], "provider_request_rejected")
        self.assertEqual(rejected["stage"], "after_request_attempt")
        self.assertEqual(started["request_id"], rejected["request_id"])
        self.assertRegex(rejected["request_id"], r"^[a-f0-9]{32}$")
        self.assertGreaterEqual(rejected["elapsed_ms"], 0)
        self.assertEqual(rejected["http_status"], 400)
        self.assertEqual(set(rejected), {"request_id", "stage", "category", "elapsed_ms",
                                        "http_status", "provider_code", "provider_param", "provider_classification",
                                        "provider_attribute_states", "provider_content_type",
                                        "provider_body_empty", "provider_request_id_present",
                                        "provider_server_header_present", "provider_via_header_present",
                                        "provider_error_object_exists", "provider_structured_fields",
                                        "provider_response_format_recognized"})
        self.assertEqual(rejected["provider_attribute_states"], structured_error_states(error))
        self.assertEqual(rejected["provider_content_type"], expected_content_type)
        self.assertEqual(rejected["provider_body_empty"], empty_body)
        self.assertEqual(rejected["provider_request_id_present"], expected_request_id_present)
        self.assertEqual(rejected["provider_server_header_present"], expected_server_header_present)
        self.assertEqual(rejected["provider_via_header_present"], expected_via_header_present)
        self.assertEqual(rejected["provider_error_object_exists"], not empty_body)
        self.assertEqual(rejected["provider_response_format_recognized"],
                         expected_content_type == "json" and not empty_body)
        combined = " ".join(captured.output) + response.text
        self.assertNotIn("DO_NOT_LOG", combined)
        self.assertNotIn("example.invalid", combined)
        if type(message) is str and len(message) > 30:
            self.assertNotIn(message, combined)
        self.assertNotIn(self.evidence[0].chunk.chunk_text, combined)
        client.chat.completions.create.assert_called_once()
        client.close.assert_called_once()
        self.assertEqual(sdk.call_args.kwargs["max_retries"], 0)
        self.assertEqual(sdk.call_args.kwargs["timeout"], 60.0)
        kwargs = client.chat.completions.create.call_args.kwargs
        self.assertEqual(set(kwargs), {"model", "store", "max_completion_tokens", "messages", "response_format"})
        self.assertEqual(kwargs["model"], "gpt-5-mini")
        self.assertEqual(kwargs["max_completion_tokens"], 400)
        self.assertFalse(kwargs["store"])
        self.assertTrue(kwargs["response_format"]["json_schema"]["strict"])
        return rejected

    def test_synthetic_sdk_http_400_response_shapes_are_sanitized(self):
        cases = (
            (b'{"code":null,"param":null,"type":null,"message":"PRIVATE_BODY"}',
             "application/json", "json", True, True, "null"),
            (b'{"error":{"code":null,"param":null,"type":null,"message":"PRIVATE_BODY"}}',
             "application/json", "json", True, True, "null"),
            (b"PRIVATE_PLAIN_ERROR", "text/plain", "text", False, False, "missing"),
            (b"<html>PRIVATE_HTML</html>", "text/html", "html", False, False, "missing"),
            (b"", "application/json", "json", False, False, "missing"),
            (b'{"error":', "application/json", "json", False, False, "missing"),
            (b"PRIVATE_BINARY", "application/octet-stream", "other", False, False, "missing"),
        )
        for raw_body, media_type, expected_type, has_error, recognized, field_type in cases:
            with self.subTest(media_type=media_type, expected_type=expected_type):
                client = OpenAI(api_key="offline-synthetic-test", max_retries=0)
                try:
                    request = httpx2.Request("POST", "https://api.openai.com/v1/chat/completions")
                    response = httpx2.Response(400, request=request,
                        headers={"content-type": media_type}, content=raw_body)
                    error = client._make_status_error_from_response(response)
                    diagnostic = provider_response_diagnostics(error)
                finally:
                    client.close()
                self.assertEqual(diagnostic["content_type_category"], expected_type)
                self.assertEqual(diagnostic["body_empty"], not raw_body)
                self.assertFalse(diagnostic["request_id_present"])
                self.assertFalse(diagnostic["server_header_present"])
                self.assertFalse(diagnostic["via_header_present"])
                self.assertEqual(diagnostic["error_object_exists"], has_error)
                self.assertEqual(diagnostic["response_format_recognized"], recognized)
                self.assertEqual(diagnostic["structured_fields"]["code"],
                                 {"exists": has_error, "type": field_type})
                self.assertNotIn("PRIVATE", json.dumps(diagnostic))

        client = OpenAI(api_key="offline-synthetic-test", max_retries=0)
        try:
            request = httpx2.Request("POST", "https://api.openai.com/v1/chat/completions")
            response = httpx2.Response(400, request=request,
                headers={"content-type": "application/json"},
                content=b'{"code":17,"param":[],"type":false,"message":"PRIVATE_BODY"}')
            error = client._make_status_error_from_response(response)
            diagnostic = provider_response_diagnostics(error)
        finally:
            client.close()
        self.assertEqual(diagnostic["structured_fields"], {
            "code": {"exists": True, "type": "number"},
            "param": {"exists": True, "type": "array"},
            "type": {"exists": True, "type": "boolean"},
        })

    def test_empty_body_400_logs_only_mime_and_header_presence(self):
        cases = (
            ({}, "missing", False, False, False),
            ({"Content-Type": "application/json; charset=utf-8",
              "X-Request-ID": "DO_NOT_LOG_PROVIDER_REQUEST_ID",
              "Server": "DO_NOT_LOG_SERVER_VALUE",
              "Via": "DO_NOT_LOG_VIA_VALUE"}, "json", True, True, True),
        )
        for headers, mime_category, request_id, server, via in cases:
            with self.subTest(mime_category=mime_category, request_id=request_id):
                rejected = self.assert_rejection_diagnostics(
                    response_headers=headers, empty_body=True,
                    expected_content_type=mime_category,
                    expected_request_id_present=request_id,
                    expected_server_header_present=server,
                    expected_via_header_present=via)
                self.assertEqual(rejected["provider_content_type"], mime_category)
                self.assertTrue(rejected["provider_body_empty"])
                self.assertEqual(rejected["provider_request_id_present"], request_id)
                self.assertEqual(rejected["provider_server_header_present"], server)
                self.assertEqual(rejected["provider_via_header_present"], via)

    def test_text_rejection_classification(self):
        cases = (
            ("Unsupported parameter: 'DO_NOT_LOG' is not supported with this model.", "unsupported_parameter"),
            ("Unsupported value: 'DO_NOT_LOG' does not support 0 with this model. Only the default value is supported.", "unsupported_value"),
            ("Invalid schema for response_format 'DO_NOT_LOG': additionalProperties must be false.", "invalid_json_schema"),
            ("Your project does not have access to model 'DO_NOT_LOG'.", "model_access_restricted"),
        )
        for message, expected in cases:
            with self.subTest(expected=expected):
                event = self.assert_rejection_diagnostics(message=message)
                self.assertEqual(event["provider_classification"], expected)

    def test_text_classifier_fails_closed(self):
        for message in (None, {}, [], 5, "", "invalid schema model", "DO_NOT_LOG" * 200,
                        "Unsupported parameter: 'model' is not supported with this model.\nDO_NOT_LOG",
                        "Invalid schema for response_format 'x': Unsupported parameter: 'model' is not supported with this model.",
                        "The model 'x' does not exist or you do not have access to it."):
            with self.subTest(kind=type(message).__name__):
                self.assertEqual(self.assert_rejection_diagnostics(message=message)["provider_classification"], "unknown")
        self.assertEqual(classify_rejection(SimpleNamespace()), "unknown")

    def test_structured_classification_precedence_and_conflict(self):
        message = "Your project does not have access to model 'DO_NOT_LOG'."
        event = self.assert_rejection_diagnostics(code="invalid_json_schema", message=message)
        self.assertEqual(event["provider_classification"], "invalid_json_schema")
        event = self.assert_rejection_diagnostics(kind="unsupported_value", message=message)
        self.assertEqual(event["provider_classification"], "unsupported_value")
        event = self.assert_rejection_diagnostics(code="invalid_json_schema", kind="unsupported_value", message=message)
        self.assertEqual(event["provider_classification"], "unknown")

    def test_allowlisted_provider_error_fields(self):
        for code in ("unsupported_parameter", "unsupported_value", "invalid_json_schema"):
            for param in ("model", "max_completion_tokens", "response_format",
                          "response_format.json_schema.schema", "store"):
                with self.subTest(code=code, param=param):
                    event = self.assert_rejection_diagnostics(code, param)
                    self.assertEqual(event["provider_code"], code)
                    self.assertEqual(event["provider_param"], param)

    def test_unknown_malicious_and_missing_provider_fields(self):
        for value in ("unknown", "model\nDO_NOT_LOG_INJECTION", {"DO_NOT_LOG": "value"}, None):
            with self.subTest(value_type=type(value).__name__):
                event = self.assert_rejection_diagnostics(value, value)
                self.assertEqual(event["provider_code"], "other")
                self.assertEqual(event["provider_param"], "other")
        event = self.assert_rejection_diagnostics(missing=True)
        self.assertEqual(event["provider_code"], "other")
        self.assertEqual(event["provider_param"], "other")

    def setUp(self):
        # Developer terminal settings must not change offline test expectations.
        environment = patch.dict("os.environ", {"AI_MAX_COMPLETION_TOKENS": "400"})
        environment.start()
        self.addCleanup(environment.stop)
        chunk = split_document_text("FICTIONAL: imaginary learners review a sample list.",
                                    document_id=1, page_no=1, source_reference="fictional://demo-campus/test",
                                    title="Fictional example", version="v1")[0]
        self.evidence = (Evidence("e1", chunk, ("learners",)),)

    def response(self, *, finish="stop", refusal=None, content='{"status":"insufficient_evidence","parts":[]}'):
        return SimpleNamespace(choices=[SimpleNamespace(finish_reason=finish,
                               message=SimpleNamespace(refusal=refusal, content=content))])

    def test_missing_configuration_never_creates_client(self):
        with patch.dict("os.environ", {}, clear=True), patch("openai.OpenAI") as sdk:
            with self.assertRaisesRegex(RuntimeError, "^provider_not_configured$"):
                OpenAIAnswerGenerator().generate("sample", self.evidence)
            sdk.assert_not_called()

    def test_sdk_request_is_bounded_structured_and_has_no_tools(self):
        with patch.dict("os.environ", {"AI_API_KEY": "fictional-test-value", "AI_MODEL": "mock-model"}), patch("openai.OpenAI") as sdk:
            client = sdk.return_value
            client.chat.completions.create.return_value = self.response()
            raw = OpenAIAnswerGenerator().generate("sample", self.evidence)
            self.assertEqual(json.loads(raw)["status"], "insufficient_evidence")
            self.assertEqual(sdk.call_args.kwargs["timeout"], 60.0)
            self.assertEqual(sdk.call_args.kwargs["max_retries"], 0)
            kwargs = client.chat.completions.create.call_args.kwargs
            self.assertEqual(kwargs["response_format"]["type"], "json_schema")
            self.assertEqual(kwargs["max_completion_tokens"], 400)
            schema = kwargs["response_format"]["json_schema"]["schema"]
            self.assertEqual(set(schema["required"]), {"status", "parts"})
            self.assertFalse(schema["additionalProperties"])
            parts = schema["properties"]["parts"]
            self.assertEqual(parts["maxItems"], 2)
            item = parts["items"]
            self.assertFalse(item["additionalProperties"])
            self.assertEqual(set(item["required"]), {"part_index", "part_text", "support", "answer_text", "evidence"})
            self.assertEqual(set(item["properties"]), set(item["required"]))
            self.assertEqual(item["properties"]["answer_text"]["type"], ["string", "null"])
            self.assertEqual(item["properties"]["evidence"]["maxItems"], 2)
            self.assertEqual(item["properties"]["evidence"]["items"]["additionalProperties"], False)
            self.assertEqual(set(item["properties"]["evidence"]["items"]["required"]),
                             {"evidence_id", "quote"})
            self.assertEqual(json.loads(raw)["parts"], [])
            self.assertIn("never silently drop", kwargs["messages"][0]["content"])

            client.chat.completions.create.assert_called_once()
            client.close.assert_called_once()
            self.assertFalse(kwargs["store"])
            self.assertNotIn("tools", kwargs)
            self.assertNotIn("fictional-test-value", json.dumps(kwargs["messages"]))
            self.assertEqual(json.loads(kwargs["messages"][1]["content"])["passages"][0]["evidence_id"], "e1")

    def test_standard_openai_api_key_environment_name_is_supported(self):
        with patch.dict("os.environ", {"OPENAI_API_KEY": "fictional-test-value", "AI_MODEL": "mock-model"}, clear=True), patch("openai.OpenAI") as sdk:
            client = sdk.return_value
            client.chat.completions.create.return_value = self.response()
            OpenAIAnswerGenerator().generate("sample", self.evidence)
            self.assertEqual(sdk.call_args.kwargs["api_key"], "fictional-test-value")
            client.chat.completions.create.assert_called_once()
            client.close.assert_called_once()

    def test_openai_api_key_takes_precedence_when_both_names_are_set(self):
        with patch.dict("os.environ", {"OPENAI_API_KEY": "standard-key", "AI_API_KEY": "legacy-key", "AI_MODEL": "mock-model"}), patch("openai.OpenAI") as sdk:
            client = sdk.return_value
            client.chat.completions.create.return_value = self.response()
            OpenAIAnswerGenerator().generate("sample", self.evidence)
            self.assertEqual(sdk.call_args.kwargs["api_key"], "standard-key")

    def test_refusal_truncation_and_missing_content_are_rejected(self):
        with patch.dict("os.environ", {"AI_API_KEY": "fictional-test-value", "AI_MODEL": "mock-model"}), patch("openai.OpenAI") as sdk:
            client = sdk.return_value
            cases = (
                (self.response(finish="length"), "provider_output_truncated", None),
                (self.response(refusal="refusal"), "selection_invalid", "refusal"),
                (self.response(content=None), "selection_invalid", "missing_content"),
                (self.response(finish="content_filter"), "selection_invalid", "non_stop_finish"),
                (SimpleNamespace(choices=[]), "selection_invalid", "empty_choices"),
            )
            for response, category, reason in cases:
                with self.subTest(category=category, response=response):
                    client.reset_mock()
                    client.chat.completions.create.return_value = response
                    with self.assertRaises(DiagnosticFailure) as raised:
                        OpenAIAnswerGenerator().generate("sample", self.evidence)
                    self.assertEqual(raised.exception.category, category)
                    self.assertEqual(raised.exception.selection_reason, reason)
                    self.assertIsNone(raised.exception.http_status)
                    client.chat.completions.create.assert_called_once()
                    client.close.assert_called_once()

    def test_completion_diagnostics_are_bounded_and_never_include_content(self):
        response = SimpleNamespace(
            _request_id="req_test_123",
            choices=[SimpleNamespace(finish_reason="stop", message=SimpleNamespace(
                content="PRIVATE_PROVIDER_OUTPUT", refusal=None))],
            usage=SimpleNamespace(prompt_tokens=51, completion_tokens=17,
                                  completion_tokens_details=SimpleNamespace(reasoning_tokens=9)),
        )
        with patch.dict("os.environ", {"AI_API_KEY": "fictional-test-value", "AI_MODEL": "mock-model"}), \
                patch("openai.OpenAI") as sdk, self.assertLogs("uvicorn.error", level="WARNING") as captured:
            sdk.return_value.chat.completions.create.return_value = response
            with diagnostic_request():
                OpenAIAnswerGenerator().generate("sample", self.evidence)
        events = [json.loads(record.getMessage()) for record in captured.records]
        received = next(event for event in events if event["category"] == "provider_response_received")
        self.assertEqual(received["completion_status"], "returned")
        self.assertEqual(received["finish_reason"], "stop")
        self.assertEqual(received["input_tokens"], 51)
        self.assertEqual(received["output_tokens"], 17)
        self.assertEqual(received["reasoning_tokens"], 9)
        self.assertEqual(received["provider_request_id"], "req_test_123")
        self.assertNotIn("PRIVATE_PROVIDER_OUTPUT", json.dumps(events))

    def test_completion_diagnostics_ignore_untrusted_metadata(self):
        response = SimpleNamespace(
            _request_id="DO_NOT_LOG secret",
            choices=[SimpleNamespace(finish_reason="DO_NOT_LOG", message=SimpleNamespace(
                content="DO_NOT_LOG", refusal=None))],
            usage=SimpleNamespace(prompt_tokens=-1, completion_tokens="DO_NOT_LOG",
                                  completion_tokens_details=SimpleNamespace(reasoning_tokens=1_000_001)),
        )
        with patch.dict("os.environ", {"AI_API_KEY": "fictional-test-value", "AI_MODEL": "mock-model"}), \
                patch("openai.OpenAI") as sdk, self.assertLogs("uvicorn.error", level="WARNING") as captured:
            sdk.return_value.chat.completions.create.return_value = response
            with diagnostic_request():
                with self.assertRaises(DiagnosticFailure):
                    OpenAIAnswerGenerator().generate("sample", self.evidence)
        serialized = " ".join(captured.output)
        self.assertNotIn("DO_NOT_LOG", serialized)
        event = next(json.loads(record.getMessage()) for record in captured.records
                     if "provider_response_received" in record.getMessage())
        self.assertEqual(event["finish_reason"], "other")
        self.assertIsNone(event["input_tokens"])
        self.assertIsNone(event["output_tokens"])
        self.assertIsNone(event["reasoning_tokens"])
        self.assertIsNone(event["provider_request_id"])


if __name__ == "__main__":
    unittest.main()
