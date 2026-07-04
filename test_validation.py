import unittest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi import HTTPException
import sys
import os
from pathlib import Path

# Ensure project root is in sys.path
sys.path.append(str(Path(__file__).resolve().parent))

import api
from api import GenerateRequest, TechProfileData, GenerateResponse


class TestGenerateValidation(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        # Create a mock TechProfileData for successful runs
        self.mock_tech_profile = TechProfileData(
            primary_language="Python",
            framework="FastAPI",
            frontend_tech="React",
            database="PostgreSQL",
            package_manager="pip",
            files_scanned=10,
            files_ignored=2
        )

    @patch("api.config.validate_environment")
    @patch("api.execute_generation_flow")
    @patch("api.save_readme")
    @patch("os.path.exists")
    @patch("os.path.isdir")
    async def test_valid_local_path(self, mock_isdir, mock_exists, mock_save, mock_execute, mock_val_env):
        # Configure mocks
        mock_exists.return_value = True
        mock_isdir.return_value = True
        mock_execute.return_value = ("# Project\nReadme content", "my_project", self.mock_tech_profile)
        mock_save.return_value = "/path/to/README.md"

        # Construct request
        req = GenerateRequest(project_path="C:/my/valid/project")
        
        # Execute
        response = await api.generate_readme(req)

        # Verify
        self.assertTrue(response.success)
        self.assertEqual(response.readme_content, "# Project\nReadme content")
        self.assertEqual(response.project_name, "my_project")
        self.assertEqual(response.saved_path, "/path/to/README.md")
        mock_execute.assert_called_once_with("C:/my/valid/project")
        mock_save.assert_called_once()

    @patch("api.config.validate_environment")
    @patch("api.clone_github_repo")
    @patch("api.execute_generation_flow")
    async def test_valid_github_url(self, mock_execute, mock_clone, mock_val_env):
        # Configure mocks
        mock_execute.return_value = ("# Repo\nReadme content", "my_github_repo", self.mock_tech_profile)

        # Construct request
        req = GenerateRequest(github_url="https://github.com/user/repo")

        # Execute
        response = await api.generate_readme(req)

        # Verify
        self.assertTrue(response.success)
        self.assertEqual(response.readme_content, "# Repo\nReadme content")
        self.assertEqual(response.project_name, "my_github_repo")
        self.assertIsNone(response.saved_path)
        mock_clone.assert_called_once()
        self.assertEqual(mock_clone.call_args[0][0], "https://github.com/user/repo")

    @patch("api.config.validate_environment")
    async def test_invalid_github_urls(self, mock_val_env):
        invalid_urls = [
            "string",
            "github.com/user/repo",  # missing scheme
            "https://gitlab.com/user/repo",  # wrong domain
            "https://github.com/user",  # missing repo
            "https://github.com//repo",  # missing owner
            "https://github.com/user/repo/tree/main",  # subpage/branch (not direct repo clone url)
        ]

        for url in invalid_urls:
            with self.subTest(url=url):
                req = GenerateRequest(github_url=url)
                with self.assertRaises(HTTPException) as ctx:
                    await api.generate_readme(req)
                self.assertEqual(ctx.exception.status_code, 400)
                self.assertIn("Invalid GitHub URL", ctx.exception.detail)

    @patch("api.config.validate_environment")
    async def test_empty_and_whitespace_validation(self, mock_val_env):
        test_cases = [
            # Both empty strings
            {"project_path": "", "github_url": ""},
            # Both whitespace
            {"project_path": "   ", "github_url": "   "},
            # Mixed empty and whitespace
            {"project_path": "", "github_url": "   "},
            {"project_path": "   ", "github_url": ""},
            # Mixed with None
            {"project_path": None, "github_url": ""},
            {"project_path": "   ", "github_url": None},
        ]

        for payload in test_cases:
            with self.subTest(payload=payload):
                req = GenerateRequest(**payload)
                with self.assertRaises(HTTPException) as ctx:
                    await api.generate_readme(req)
                self.assertEqual(ctx.exception.status_code, 400)
                self.assertIn("Provide either 'project_path' or 'github_url'", ctx.exception.detail)

    @patch("api.config.validate_environment")
    async def test_null_values(self, mock_val_env):
        # Both None
        req = GenerateRequest(project_path=None, github_url=None)
        with self.assertRaises(HTTPException) as ctx:
            await api.generate_readme(req)
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("Provide either 'project_path' or 'github_url'", ctx.exception.detail)

    @patch("api.config.validate_environment")
    @patch("api.execute_generation_flow")
    @patch("api.save_readme")
    @patch("os.path.exists")
    @patch("os.path.isdir")
    async def test_whitespace_trimming_and_execution(self, mock_isdir, mock_exists, mock_save, mock_execute, mock_val_env):
        mock_exists.return_value = True
        mock_isdir.return_value = True
        mock_execute.return_value = ("# Project", "my_project", self.mock_tech_profile)
        mock_save.return_value = "/path/to/README.md"

        # Project path has whitespace
        req = GenerateRequest(project_path="  C:/my/valid/project   ")
        response = await api.generate_readme(req)
        self.assertTrue(response.success)
        mock_execute.assert_called_with("C:/my/valid/project")

    @patch("api.config.validate_environment")
    @patch("api.clone_github_repo")
    @patch("api.execute_generation_flow")
    async def test_github_whitespace_trimming(self, mock_execute, mock_clone, mock_val_env):
        mock_execute.return_value = ("# Repo", "my_github_repo", self.mock_tech_profile)

        # GitHub URL has whitespace
        req = GenerateRequest(github_url="   https://github.com/user/repo.git   ")
        response = await api.generate_readme(req)
        self.assertTrue(response.success)
        mock_clone.assert_called_with("https://github.com/user/repo.git", unittest.mock.ANY)

    @patch("api.config.validate_environment")
    @patch("api.execute_generation_flow")
    @patch("api.save_readme")
    @patch("os.path.exists")
    @patch("os.path.isdir")
    async def test_precedence_prefer_local(self, mock_isdir, mock_exists, mock_save, mock_execute, mock_val_env):
        mock_exists.return_value = True
        mock_isdir.return_value = True
        mock_execute.return_value = ("# Local", "local_proj", self.mock_tech_profile)
        mock_save.return_value = "/path/to/README.md"

        # Both supplied, github_mode is False/None
        req = GenerateRequest(
            project_path="C:/local/path",
            github_url="https://github.com/user/repo",
            github_mode=None
        )
        response = await api.generate_readme(req)
        self.assertTrue(response.success)
        mock_execute.assert_called_once_with("C:/local/path")

    @patch("api.config.validate_environment")
    @patch("api.clone_github_repo")
    @patch("api.execute_generation_flow")
    async def test_precedence_explicit_github(self, mock_execute, mock_clone, mock_val_env):
        mock_execute.return_value = ("# GitHub", "github_proj", self.mock_tech_profile)

        # Both supplied, github_mode is True
        req = GenerateRequest(
            project_path="C:/local/path",
            github_url="https://github.com/user/repo",
            github_mode=True
        )
        response = await api.generate_readme(req)
        self.assertTrue(response.success)
        mock_clone.assert_called_once()
        self.assertEqual(mock_clone.call_args[0][0], "https://github.com/user/repo")


if __name__ == "__main__":
    unittest.main()
