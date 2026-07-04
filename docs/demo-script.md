# Demo Video Script (5 Minutes)

This script outlines the narration and visual cues for a 5-minute presentation demo of README Copilot for the Kaggle Capstone.

---

## ⏱️ Video Breakdown

| Segment | Topic | Target Duration |
| :--- | :--- | :--- |
| **1** | Introduction & Problem Statement | 0:00 - 1:00 (60s) |
| **2** | The Solution (Multi-Agent Design) | 1:00 - 1:45 (45s) |
| **3** | System Architecture & MCP | 1:45 - 2:30 (45s) |
| **4** | Live Demo (CLI Execution) | 2:30 - 3:45 (75s) |
| **5** | Output Walkthrough (Generated README) | 3:45 - 4:30 (45s) |
| **6** | Closing & Future Enhancements | 4:30 - 5:00 (30s) |

---

## 🎤 Narration Script

### 1. Introduction & Problem Statement (60 seconds)
- **Visual**: Show title slide: *README Copilot – Multi-Agent AI Documentation Generator*. Show a GitHub repository page with an empty or messy README.
- **Narrator**: 
  > "Hello everyone, my name is [Your Name], and today I am excited to present **README Copilot**, built for the Kaggle AI Agents Intensive Capstone.
  > 
  > Let's start with a problem we all face: documentation. We know that good documentation improves project onboarding, collaboration, and repository health. Yet, writing and maintaining a comprehensive README is a repetitive chore that developers frequently neglect or push to the side. As a result, GitHub is filled with repositories lacking clear instructions.
  > 
  > Standard LLM wrapper prompts try to write documentation in one go, but they often hallucinate, miss critical files, mix up schemas, or risk leaking API keys. README Copilot solves this problem by using a modular, multi-agent AI architecture."

### 2. The Solution (45 seconds)
- **Visual**: Show a diagram of the three agents: Planner Agent, Project Analyzer Agent, and README Generator Agent.
- **Narrator**:
  > "Instead of a single monolithic prompt, README Copilot employs exactly three specialized AI agents coordinated by a clean CLI controller.
  > 
  > First, our **Planner Agent** reviews top-level files to establish a documentation scope and execution checklist. 
  > Next, our **Project Analyzer Agent** scans the workspace configurations to build a strict technology profile.
  > Finally, our **README Generator Agent** translates that structured profile into production-quality Markdown.
  > 
  > This division of labor keeps each agent focused, prevents prompt token bloat, and enforces robust structured outputs."

### 3. System Architecture & MCP (45 seconds)
- **Visual**: Show the high-level architecture diagram. Highlight the **Local MCP Server** subprocess.
- **Narrator**:
  > "An important part of our architecture is security. AI models should not have unconstrained access to write or execute commands directly on your files.
  > 
  > To address this, we integrated the **Model Context Protocol**, or MCP. Our Project Analyzer Agent maps the project directory *only* by invoking standard tools exposed by a local MCP server.
  > This server runs as an isolated subprocess using stdio transport. It implements strict validation rules: it blocks directory traversal, ignores build artifacts, and completely rejects reading environment `.env` files or certificates.
  > This guarantees that real credentials never leak to the model."

### 4. Live Demo (75 seconds)
- **Visual**: Transition to terminal screen. Execute the command: `python app.py "c:\Users\gadam\Smart ReadME"`.
- **Narrator**:
  > "Let's see it in action. I'll launch our Typer-based CLI and point it to our own project directory.
  > 
  > Notice the clean welcome banner. Right away, the **Planner Agent** starts, analyzes our folder structure, and coordinates our plan.
  > 
  > Now, the **Project Analyzer Agent** connects to our local MCP server. It's scanning config files like requirements.txt and package.json to identify frameworks.
  > 
  > Once the tech profile JSON is created, the **README Generator Agent** compiles it into a structured markdown document, drafting install commands and rendering a custom Mermaid flow diagram.
  > 
  > And we're done! The CLI outputs a gorgeous **Execution Summary Panel** highlighting the tech profile, files scanned, and the elapsed time—just under 10 seconds."

### 5. Output Walkthrough (45 seconds)
- **Visual**: Open the generated `README.md` in an editor or GitHub preview. Scroll through sections.
- **Narrator**:
  > "Let's open the generated `README.md`. As you can see, this is a premium, professional document.
  > 
  > We have a clear title, key features list, and a neat technology stack table. The directory tree was automatically mapped, and the installation commands are tailored to our pip package manager.
  > 
  > Most importantly, look at the architecture section. README Copilot generated a syntactically correct **Mermaid flowchart** that visually maps out our execution flow. There are no TODO placeholders—everything is complete, polished, and ready for production."

### 6. Closing (30 seconds)
- **Visual**: Show contact/project link slide.
- **Narrator**:
  > "README Copilot demonstrates how Google ADK and the Model Context Protocol can be combined to build highly secure, modular, and visual agentic workflows.
  > 
  > Thank you for your time. The code, documentation, and Kaggle writeup are fully open source and ready in the repository. I look forward to your feedback!"
