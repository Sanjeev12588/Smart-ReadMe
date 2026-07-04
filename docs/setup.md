# Installation & Setup Guide

This guide explains how to install dependencies, configure environment settings, and run the README Copilot application for local development.

---

## 📋 System Requirements

- **OS**: Windows, macOS, or Linux
- **Python**: Version 3.12 or newer
- **Internet Access**: Required to interact with Google Gemini models

---

## 🛠️ Step-by-Step Installation

### 1. Clone the Codebase
Download the repository files to your local machine:
```bash
git clone https://github.com/your-username/readme-copilot.git
cd readme-copilot
```

### 2. Configure Virtual Environment
We recommend using Python's built-in `venv` module to isolate project dependencies:
```bash
# Initialize venv folder
python -m venv venv

# Activate on Linux/macOS
source venv/bin/activate

# Activate on Windows (Command Prompt)
venv\Scripts\activate

# Activate on Windows (PowerShell)
.\venv\Scripts\Activate.ps1
```

### 3. Install Package Dependencies
Install the required packages declared in `requirements.txt`:
```bash
pip install -r requirements.txt
```
This installs the core packages:
- `google-adk`: The agentic structure framework.
- `google-genai`: The client libraries to query Gemini models.
- `fastmcp` & `mcp`: Protocal SDKs for filesystem tools.
- `rich` & `typer`: CLI visualization and parsing tools.
- `python-dotenv`: Management helper for environment files.

---

## ⚙️ Environment Configuration

README Copilot relies on environment variables for API keys and default models.

### Create Environment File
Create a file named `.env` in the root of the project directory:
```env
# Google Gemini API key (Required)
GEMINI_API_KEY=your_gemini_api_key_here

# Default Gemini model (Optional - defaults to gemini-2.5-flash)
GEMINI_MODEL=gemini-2.5-flash
```

> [!IMPORTANT]
> The `.env` file contains sensitive credentials and must **never** be committed to public repositories. A `.gitignore` entry is configured to block it. Only `.env.example` should be checked in.

---

## 🚀 Running the CLI

Run the tool by targeting python at `app.py`:

```bash
# Pass project path as an argument
python app.py "C:\Projects\MyProject"

# Or run interactively (you will be prompted to enter the path)
python app.py
```
Upon successful execution, a `README.md` will be saved directly inside your target repository directory, and a detailed summary panel will print in the console.
