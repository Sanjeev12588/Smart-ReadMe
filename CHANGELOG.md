# Changelog

All notable changes to the README Copilot project will be documented in this file. This project follows [Semantic Versioning](https://semver.org/).

---

## [1.0.0-MVP] - 2026-07-03

This is the initial release of README Copilot for the Kaggle AI Agents Intensive Capstone submission.

### Added
- **Multi-Agent Architecture**: Planner Agent, Project Analyzer Agent, and README Generator Agent coordinated sequentially via `app.py`.
- **Model Context Protocol (MCP) Server**: Python subprocess FastMCP server with file listing, safe file reading, ASCII directory mapping, and configuration batch reading tools.
- **Rich CLI UI**: Custom console banner, progress status spinners, and a post-execution summary panel listing languages, dependencies, and scanned files.
- **Static Tech Detectors**: Regex-based parsers to statically identify Python/JS/TS environments, FastAPI/Flask/Django/React/Next.js frameworks, and configuration keys.
- **GitHub Documentation**: Premium root landing page README, sequence flowchart maps, and detailed sub-guides (`setup.md`, `agent-design.md`, `mcp.md`, `architecture.md`).
- **Open Source Files**: `LICENSE` (MIT), `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`, and `CHANGELOG.md`.
