"""Tests for native structured-output schema builders and the graceful-degrade helper.

Structured output forces valid, correctly-shaped JSON at generation time (grammar-constrained on
local servers). These cover the pure builders and the "retry without the schema if the provider
rejects it" fallback that keeps the feature universal and safe. Real provider calls aren't
exercised in CI (no network)."""
import unittest

from libriscribe.utils import structured_output as so
from libriscribe.utils.llm_client import _call_or_degrade, _is_schema_error


class SchemaBuilderTests(unittest.TestCase):
    def test_fields_schema_shape(self):
        schema = so.json_schema_for_fields(["role", "background"])
        self.assertEqual(schema["type"], "object")
        self.assertEqual(set(schema["properties"]), {"role", "background"})
        self.assertEqual(schema["properties"]["role"], {"type": "string"})
        self.assertEqual(schema["required"], ["role", "background"])  # present-but-may-be-empty
        self.assertFalse(schema["additionalProperties"])

    def test_classify_schema_enum(self):
        schema = so.classify_schema()
        self.assertEqual(schema["properties"]["category"]["enum"], ["character", "location", "lore", "arc"])
        self.assertIn("fields", schema["properties"])
        self.assertEqual(schema["required"], ["category", "fields"])

    def test_response_format_openai_envelope(self):
        rf = so.response_format_openai(so.json_schema_for_fields(["role"]), name="lore")
        self.assertEqual(rf["type"], "json_schema")
        self.assertEqual(rf["json_schema"]["name"], "lore")
        self.assertIn("schema", rf["json_schema"])

    def test_response_format_json_object(self):
        self.assertEqual(so.response_format_json_object(), {"type": "json_object"})

    def test_cats_schema_shape(self):
        schema = so.cats_schema()
        self.assertEqual(set(schema["properties"]), {"characters", "locations", "lore", "arcs"})
        item = schema["properties"]["characters"]["items"]
        self.assertEqual(item["required"], ["name"])  # each entity must have a name

    def test_strict_auto_off_for_open_schema(self):
        # cats_schema has open entity items -> must NOT be strict (strict needs closed objects)
        rf = so.response_format_openai(so.cats_schema())
        self.assertFalse(rf["json_schema"]["strict"])

    def test_strict_auto_on_for_closed_schema(self):
        rf = so.response_format_openai(so.json_schema_for_fields(["role"]))
        self.assertTrue(rf["json_schema"]["strict"])


class GracefulDegradeTests(unittest.TestCase):
    def test_is_schema_error_typeerror(self):
        self.assertTrue(_is_schema_error(TypeError("unexpected keyword argument 'response_format'")))

    def test_is_schema_error_message_token(self):
        self.assertTrue(_is_schema_error(ValueError("400: response_format not supported by this model")))
        self.assertTrue(_is_schema_error(Exception("Invalid response_mime_type for this model")))

    def test_is_not_schema_error_for_unrelated(self):
        self.assertFalse(_is_schema_error(TimeoutError("read timed out")))
        self.assertFalse(_is_schema_error(ValueError("401 Unauthorized: bad api key")))

    def test_call_or_degrade_falls_back_on_schema_error(self):
        calls = []

        def with_schema():
            calls.append("with")
            raise ValueError("400 invalid response_format json_schema")

        def without_schema():
            calls.append("without")
            return "plain result"

        self.assertEqual(_call_or_degrade(with_schema, without_schema), "plain result")
        self.assertEqual(calls, ["with", "without"])

    def test_call_or_degrade_reraises_non_schema_error(self):
        def with_schema():
            raise TimeoutError("read timed out")

        def without_schema():
            raise AssertionError("should not be called for non-schema errors")

        with self.assertRaises(TimeoutError):
            _call_or_degrade(with_schema, without_schema)

    def test_call_or_degrade_passthrough_on_success(self):
        self.assertEqual(_call_or_degrade(lambda: "ok", lambda: "fallback"), "ok")


class JsonValidationGateTests(unittest.TestCase):
    """generate_content_with_json_repair must accept BARE JSON (what structured output and clean
    instruct models emit) — the old fence-only gate rejected it and failed to an empty string,
    which is why lore extraction returned {} and classification fell back to lore on every model."""
    def _client(self, canned_response):
        from libriscribe.utils.llm_client import LLMClient
        c = LLMClient("local")
        c._generate_once = lambda *a, **k: canned_response  # bypass the network
        return c

    def test_bare_json_passes_without_failing(self):
        from libriscribe.utils.file_utils import parse_llm_json
        c = self._client('{"role": "technician", "physical_description": "tall"}')
        out = c.generate_content_with_json_repair("x", json_schema={"type": "object"})
        self.assertEqual(parse_llm_json(out), {"role": "technician", "physical_description": "tall"})

    def test_preamble_then_bare_json_passes(self):
        from libriscribe.utils.file_utils import parse_llm_json
        c = self._client('Sure, here you go:\n{"category": "character"}')
        out = c.generate_content_with_json_repair("x")
        self.assertEqual(parse_llm_json(out), {"category": "character"})

    def test_fenced_json_still_works(self):
        from libriscribe.utils.file_utils import parse_llm_json
        c = self._client('```json\n{"a": 1}\n```')
        out = c.generate_content_with_json_repair("x")
        self.assertEqual(parse_llm_json(out), {"a": 1})


if __name__ == "__main__":
    unittest.main()
