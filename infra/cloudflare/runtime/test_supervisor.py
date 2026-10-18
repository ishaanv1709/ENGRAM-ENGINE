"""Startup boundary checks without credentials or cloud resource creation."""

import importlib.util
import os
from pathlib import Path
import unittest
from unittest.mock import patch

from cryptography.fernet import Fernet

spec = importlib.util.spec_from_file_location("cloud_supervisor", Path(__file__).with_name("supervisor.py"))
supervisor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(supervisor)


class RuntimeBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.env = {
            "DATABASE_URL": "postgresql://fixture:fixture@sql.example.test/engram?sslmode=require",
            "FALKOR_HOST": "graph.example.test", "FALKOR_TLS": "true", "FALKOR_PASSWORD": "fixture",
            "QDRANT_URL": "https://vector.example.test:6333", "QDRANT_API_KEY": "fixture",
            "ARTIFACT_SERVICE_ORIGIN": "https://artifacts.example.test", "ARTIFACT_SERVICE_TOKEN": "fixture",
            "PROVIDER_ENCRYPTION_KEY": Fernet.generate_key().decode(), "MEM0_HISTORY_BACKEND": "postgres",
            "ARTIFACT_BACKEND": "r2", "ORIGINS": '["https://engram.example.test"]',
        }

    def validate(self, **changes):
        with patch.dict(os.environ, {**self.env, **changes}, clear=True):
            supervisor.validate_environment()

    def test_external_tls_configuration_is_accepted_without_connecting(self):
        self.validate()

    def test_local_and_unencrypted_stores_are_rejected(self):
        cases = [
            {"DATABASE_URL": "postgresql://u:p@127.0.0.1/db?sslmode=require"},
            {"DATABASE_URL": "postgresql://u:p@sql.example.test/db"},
            {"FALKOR_HOST": "localhost"}, {"FALKOR_TLS": "false"},
            {"QDRANT_URL": "http://vector.example.test:6333"},
            {"ARTIFACT_SERVICE_ORIGIN": "https://127.0.0.1"},
            {"MEM0_HISTORY_BACKEND": "sqlite"}, {"ARTIFACT_BACKEND": "local"},
        ]
        for changes in cases:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.validate(**changes)

    def test_missing_or_placeholder_and_operator_keys_are_rejected(self):
        for changes in ({"QDRANT_API_KEY": "****"}, {"PROVIDER_ENCRYPTION_KEY": ""},
                        {"GROQ_API_KEY": "not-a-real-key"}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.validate(**changes)


if __name__ == "__main__":
    unittest.main()
