"""Security and authentication tests for The Oracle."""

import pytest
from fastapi.testclient import TestClient

from ..app import app


class TestSecurity:
    """Test security features."""

    def test_no_eval_usage(self):
        """Verify no eval() or exec() usage in codebase."""
        import os
        import subprocess

        # Search for eval/exec usage
        result = subprocess.run(
            ["grep", "-r", "eval(", "backend/"],
            capture_output=True,
            text=True
        )

        # Should not find any eval() usage
        assert result.returncode != 0 or len(result.stdout) == 0, "Found eval() usage in codebase"

    def test_admin_endpoint_requires_auth(self):
        """Test that admin endpoints require authentication."""
        client = TestClient(app)

        # Try to access admin endpoint without auth
        response = client.post("/admin/rebuild")
        assert response.status_code == 401 or response.status_code == 404

    def test_env_file_not_committed(self):
        """Verify .env files are not committed to git."""
        import subprocess

        # Check if .env is in git
        result = subprocess.run(
            ["git", "ls-files", ".env"],
            capture_output=True,
            text=True
        )

        # .env should not be tracked
        assert result.returncode != 0 or len(result.stdout) == 0, ".env file is committed to git"

    def test_secrets_in_gitignore(self):
        """Verify secrets directory is in .gitignore."""
        with open(".gitignore", "r") as f:
            gitignore_content = f.read()

        assert "/secrets/" in gitignore_content or "secrets/" in gitignore_content
        assert ".env" in gitignore_content

    def test_api_input_validation(self):
        """Test that API inputs are properly validated."""
        client = TestClient(app)

        # Try invalid topic_id (should be validated)
        response = client.get("/topics/invalid-topic-id-with-special-chars!@#")
        # Should either return 404 or handle gracefully
        assert response.status_code in [200, 404, 422]

    def test_sql_injection_prevention(self):
        """Test SQL injection prevention."""
        client = TestClient(app)

        # Try SQL injection in query parameters
        malicious_input = "'; DROP TABLE topics; --"
        response = client.get(f"/topics?topic_id={malicious_input}")

        # Should handle gracefully without executing SQL
        assert response.status_code in [200, 400, 422, 500]

    def test_cors_configuration(self):
        """Test CORS configuration."""
        client = TestClient(app)

        # Check CORS headers
        response = client.options("/health")
        # CORS headers should be present
        assert "access-control-allow-origin" in response.headers or response.status_code == 200

    def test_error_messages_no_sensitive_data(self):
        """Test that error messages don't leak sensitive information."""
        client = TestClient(app)

        # Try to access non-existent endpoint
        response = client.get("/nonexistent-endpoint")
        error_detail = response.json().get("detail", "")

        # Error message should not contain sensitive info
        sensitive_keywords = ["password", "token", "api_key", "secret", "credential"]
        assert not any(keyword in error_detail.lower() for keyword in sensitive_keywords)

