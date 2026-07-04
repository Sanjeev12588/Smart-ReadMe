# Contributing to README Copilot

Thank you for your interest in contributing to README Copilot! As a submission for the Kaggle AI Agents Intensive Capstone, we welcome feedback, bug reports, and enhancements to help make this tool more robust.

---

## 🧭 Code of Conduct
By participating in this project, you agree to abide by our [Code of Conduct](CODE_OF_CONDUCT.md).

---

## 🐛 Reporting Bugs & Issues
If you encounter an issue or have a feature suggestion:
1. Search the existing issues to check if it has already been reported.
2. If not, open a new issue describing:
   - Your OS and Python version.
   - Clear steps to reproduce the bug.
   - The expected vs. actual output (including full stack traces if applicable).

---

## 🛠️ Development & Coding Standards

We follow these guidelines:
- **Style Compliance**: All Python scripts should follow PEP 8 styling conventions.
- **Type Safety**: Use type hints on all public function parameters and return targets.
- **Document Integrity**: Add descriptive docstrings to all new modules, classes, and helper functions.
- **Agent Guidelines**: Avoid nesting agent execution calls directly inside model prompts. Coordinate agent pipelines sequentially inside `app.py`.
- **Security Check**: Never commit `.env` variables or real API keys to the codebase. Ensure config ignores are updated if new secret-bearing configurations are introduced.

---

## 🚀 Proposing Changes (Pull Requests)

Follow this workflow to submit improvements:
1. Fork the repository and create a descriptive branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```
2. Implement your changes, adding comments where necessary.
3. Test your changes against local workspaces to verify that `app.py` runs without exceptions:
   ```bash
   python app.py "C:\path\to\test\workspace"
   ```
4. Commit your edits with clean, descriptive commit messages:
   ```bash
   git commit -m "feat: add Go module technology parser to detector"
   ```
5. Push to your fork and submit a Pull Request (PR) referencing the related issue.
