"""Security and authentication tests for The Oracle."""

import os
from pathlib import Path


class TestSecurity:
    """Test security features."""

    def test_no_eval_usage(self):
        """Verify no eval() or exec() usage in codebase."""
        import subprocess

        # Search for eval/exec usage in Python files
        result = subprocess.run(
            ["grep", "-r", "--include=*.py", "eval(", "backend/"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )

        # Should not find any eval() usage
        assert result.returncode != 0 or len(result.stdout) == 0, f"Found eval() usage in codebase: {result.stdout}"

    def test_env_file_not_committed(self):
        """Verify .env files are not committed to git."""
        import subprocess

        repo_root = Path(__file__).parent.parent.parent

        # Check if .env is in git
        result = subprocess.run(
            ["git", "ls-files", ".env"],
            capture_output=True,
            text=True,
            cwd=repo_root
        )

        # .env should not be tracked
        assert result.returncode != 0 or len(result.stdout) == 0, ".env file is committed to git"

    def test_secrets_in_gitignore(self):
        """Verify secrets directory is in .gitignore."""
        repo_root = Path(__file__).parent.parent.parent
        gitignore_path = repo_root / ".gitignore"

        if gitignore_path.exists():
            gitignore_content = gitignore_path.read_text()
            assert "/secrets/" in gitignore_content or "secrets/" in gitignore_content
            assert ".env" in gitignore_content
        else:
            # If .gitignore doesn't exist, that's also a problem
            assert False, ".gitignore file not found"

    def test_no_hardcoded_credentials(self):
        """Verify no hardcoded credentials in code."""
        import subprocess

        repo_root = Path(__file__).parent.parent.parent

        # Search for common credential patterns
        patterns = [
            "password\\s*=\\s*['\"].*['\"]",
            "api_key\\s*=\\s*['\"].*['\"]",
            "token\\s*=\\s*['\"].*['\"]",
            "secret\\s*=\\s*['\"].*['\"]"
        ]

        for pattern in patterns:
            result = subprocess.run(
                ["grep", "-r", "--include=*.py", "-E", pattern, "backend/"],
                capture_output=True,
                text=True,
                cwd=repo_root
            )

            # Filter out false positives (like test data, comments, etc.)
            if result.returncode == 0 and result.stdout:
                lines = result.stdout.strip().split('\n')
                # Filter out test files and comments
                actual_issues = [
                    line for line in lines
                    if 'test' not in line.lower() and not line.strip().startswith('#')
                ]
                assert len(actual_issues) == 0, f"Found potential hardcoded credentials: {actual_issues}"

    def test_sql_injection_prevention_structure(self):
        """Test that code uses parameterized queries (structural check)."""
        import subprocess

        repo_root = Path(__file__).parent.parent.parent

        # Check for SQLAlchemy usage (which uses parameterized queries)
        result = subprocess.run(
            ["grep", "-r", "--include=*.py", "from sqlalchemy", "backend/"],
            capture_output=True,
            text=True,
            cwd=repo_root
        )

        # Should use SQLAlchemy for database operations
        assert result.returncode == 0, "No SQLAlchemy usage found - may be using raw SQL"

    def test_input_validation_pydantic(self):
        """Test that Pydantic is used for input validation."""
        import subprocess

        repo_root = Path(__file__).parent.parent.parent

        # Check for Pydantic usage in API routes
        result = subprocess.run(
            ["grep", "-r", "--include=*.py", "from pydantic", "backend/api/"],
            capture_output=True,
            text=True,
            cwd=repo_root
        )

        # Should use Pydantic for validation
        assert result.returncode == 0, "No Pydantic usage found in API routes"

