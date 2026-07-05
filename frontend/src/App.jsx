import React, { useState, useEffect } from 'react';
import { marked } from 'marked';

// Frontend request timeout (must be slightly longer than backend PIPELINE_TIMEOUT_SECONDS=300)
const FETCH_TIMEOUT_MS = 330_000; // 5.5 minutes

// Dynamically determine the backend URL.
// If the app is run via the Vite local dev server (port is not 8050), point to localhost:8050.
// If served by FastAPI directly (locally or on Railway), use a relative URL path.
const getApiUrl = (path) => {
  if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
    if (window.location.port !== '8050') {
      return `http://127.0.0.1:8050${path}`;
    }
  }
  return path;
};

function App() {
  // Input states
  const [inputSource, setInputSource] = useState('path'); // 'path' or 'url'
  const [projectPath, setProjectPath] = useState('');
  const [githubUrl, setGithubUrl] = useState('');
  
  // Loading & Step states
  const [isLoading, setIsLoading] = useState(false);
  const [agentStep, setAgentStep] = useState(0); // 0: Idle, 1: Planning, 2: Analyzing, 3: Generating, 4: Finished, -1: Error
  const [statusText, setStatusText] = useState('');
  
  // Response states
  const [readmeContent, setReadmeContent] = useState('');
  const [projectName, setProjectName] = useState('');
  const [techProfile, setTechProfile] = useState(null);
  const [executionTime, setExecutionTime] = useState(0);
  const [savedPath, setSavedPath] = useState('');
  const [errorMessage, setErrorMessage] = useState('');

  // Setup markdown parser configuration to render safe HTML
  useEffect(() => {
    marked.setOptions({
      breaks: true,
      gfm: true
    });
  }, []);

  // Update status messages based on current agent step
  useEffect(() => {
    switch (agentStep) {
      case 1:
        setStatusText('Planner Agent: Reading folder layout and building execution checklist...');
        break;
      case 2:
        setStatusText('Project Analyzer Agent: Connected to local MCP Server. Scanning config files...');
        break;
      case 3:
        setStatusText('README Generator Agent: Synthesizing technology schemas into premium markdown copy...');
        break;
      case 4:
        setStatusText('Execution Completed Successfully!');
        break;
      case -1:
        setStatusText('An error occurred during multi-agent orchestration.');
        break;
      default:
        setStatusText('Ready to analyze workspace.');
    }
  }, [agentStep]);

  // Handle generation call
  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    setErrorMessage('');
    setReadmeContent('');
    setTechProfile(null);
    setSavedPath('');
    setAgentStep(1); // Set to Planning

    // Simulated progress transitions to make the UI feel responsive and alive
    const stepInterval = setInterval(() => {
      setAgentStep((prev) => {
        if (prev === 1) return 2; // Move to Analyzing
        if (prev === 2) return 3; // Move to Generating
        return prev;
      });
    }, 6000);

    // AbortController allows us to cancel the fetch after FETCH_TIMEOUT_MS.
    // Without this, if the backend hangs, the browser shows "Failed to fetch"
    // after the OS-level TCP timeout (~2 min on most systems) with no context.
    const controller = new AbortController();
    const timeoutId = setTimeout(() => {
      controller.abort();
    }, FETCH_TIMEOUT_MS);

    try {
      const payload = {};
      if (inputSource === 'path') {
        payload.project_path = projectPath;
      } else {
        payload.github_url = githubUrl;
      }

      let response;
      try {
        response = await fetch(getApiUrl('/api/generate'), {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(payload),
          signal: controller.signal,
        });
      } catch (networkErr) {
        // Distinguish between timeout abort and genuine network failure
        if (networkErr.name === 'AbortError') {
          throw new Error(
            `Request timed out after ${Math.round(FETCH_TIMEOUT_MS / 60000)} minutes. ` +
            'The repository may be too large or the AI model is under heavy load. ' +
            'Please try again.'
          );
        }
        // Network-level failure (backend not running, connection refused, etc.)
        throw new Error(
          `Cannot reach the backend server at ${getApiUrl('/api/generate')}. ` +
          'Please make sure the FastAPI backend is running (e.g. python api.py)'
        );
      }

      clearInterval(stepInterval);
      clearTimeout(timeoutId);

      if (!response.ok) {
        // Server returned an HTTP error (4xx or 5xx) — parse the JSON detail
        let errorDetail = `Server error (HTTP ${response.status})`;
        try {
          const errorData = await response.json();
          errorDetail = errorData.detail || errorDetail;
        } catch {
          // If the error body is not JSON, use the status text
          errorDetail = response.statusText || errorDetail;
        }
        throw new Error(errorDetail);
      }

      const data = await response.json();
      
      setAgentStep(4); // Finished
      setReadmeContent(data.readme_content);
      setProjectName(data.project_name);
      setTechProfile(data.tech_profile);
      setExecutionTime(data.execution_time);
      setSavedPath(data.saved_path);
    } catch (err) {
      clearInterval(stepInterval);
      clearTimeout(timeoutId);
      setAgentStep(-1); // Error
      setErrorMessage(err.message || 'An unexpected error occurred.');
    } finally {
      setIsLoading(false);
    }
  };

  // Copy Markdown to Clipboard
  const handleCopy = () => {
    navigator.clipboard.writeText(readmeContent);
    alert('Copied README content to clipboard!');
  };

  // Download README.md
  const handleDownload = () => {
    const element = document.createElement('a');
    const file = new Blob([readmeContent], { type: 'text/plain;charset=utf-8' });
    element.href = URL.createObjectURL(file);
    element.download = 'README.md';
    document.body.appendChild(element);
    element.click();
    document.body.removeChild(element);
  };

  return (
    <div className="app-container">
      {/* Header */}
      <header>
        <div className="logo-container">
          <div className="logo-icon">🚀</div>
          <div className="logo-text">
            <h1>README COPILOT</h1>
            <p>MULTI-AGENT AI DOCUMENTATION GENERATOR</p>
          </div>
        </div>
        <div className="api-badge" style={{ fontSize: '0.8rem', color: '#9e9eb0', background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.05)', padding: '0.3rem 0.6rem', borderRadius: '6px' }}>
          API: <span style={{ color: '#00e676', fontWeight: 600 }}>ONLINE</span>
        </div>
      </header>

      {/* Main Workspace */}
      <div style={{ display: 'grid', gridTemplateColumns: '350px 1fr', gap: '2rem' }}>
        
        {/* Left Control Panel */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          
          {/* Target Selection Panel */}
          <div className="glass-panel">
            <h3 className="form-title">⚡ Workspace Scopes</h3>
            <form onSubmit={handleSubmit}>
              
              <div className="toggle-group">
                <button 
                  type="button" 
                  className={`toggle-btn ${inputSource === 'path' ? 'active' : ''}`}
                  onClick={() => setInputSource('path')}
                >
                  Local Path
                </button>
                <button 
                  type="button" 
                  className={`toggle-btn ${inputSource === 'url' ? 'active' : ''}`}
                  onClick={() => setInputSource('url')}
                >
                  GitHub URL
                </button>
              </div>

              {inputSource === 'path' ? (
                <div className="input-container">
                  <label htmlFor="projectPath">LOCAL PROJECT DIRECTORY</label>
                  <input
                    id="projectPath"
                    type="text"
                    className="input-field"
                    placeholder="e.g. C:\Projects\HostelFinder"
                    value={projectPath}
                    onChange={(e) => setProjectPath(e.target.value)}
                    required={inputSource === 'path'}
                    disabled={isLoading}
                  />
                </div>
              ) : (
                <div className="input-container">
                  <label htmlFor="githubUrl">GITHUB REPOSITORY URL</label>
                  <input
                    id="githubUrl"
                    type="url"
                    className="input-field"
                    placeholder="e.g. https://github.com/user/repo"
                    value={githubUrl}
                    onChange={(e) => setGithubUrl(e.target.value)}
                    required={inputSource === 'url'}
                    disabled={isLoading}
                  />
                </div>
              )}

              <button type="submit" className="submit-btn" disabled={isLoading}>
                {isLoading ? (
                  <>
                    <div className="spinner"></div> Running Agents...
                  </>
                ) : (
                  'Build README.md'
                )}
              </button>
            </form>
          </div>

          {/* Agent Activity Log Panel */}
          {(isLoading || agentStep !== 0) && (
            <div className="glass-panel">
              <h3 className="form-title">🤖 Multi-Agent Orchestrator</h3>
              
              <div className="timeline-container">
                <div className={`timeline-step ${agentStep === 1 ? 'active' : ''} ${agentStep > 1 ? 'completed' : ''}`}>
                  <div className="step-indicator">{agentStep > 1 ? '✔' : '1'}</div>
                  <div className="step-details">
                    <h4>Planner Agent</h4>
                    <p>Creating documentation schedule</p>
                  </div>
                </div>
                
                <div className={`timeline-step ${agentStep === 2 ? 'active' : ''} ${agentStep > 2 ? 'completed' : ''}`}>
                  <div className="step-indicator">{agentStep > 2 ? '✔' : '2'}</div>
                  <div className="step-details">
                    <h4>Project Analyzer Agent</h4>
                    <p>Scanning files &amp; configs via MCP</p>
                  </div>
                </div>
                
                <div className={`timeline-step ${agentStep === 3 ? 'active' : ''} ${agentStep > 3 ? 'completed' : ''}`}>
                  <div className="step-indicator">{agentStep > 3 ? '✔' : '3'}</div>
                  <div className="step-details">
                    <h4>README Writer Agent</h4>
                    <p>Generating final markdown outputs</p>
                  </div>
                </div>
              </div>

              <div style={{ marginTop: '1.5rem', borderTop: '1px solid rgba(255,255,255,0.05)', paddingTop: '1rem' }}>
                <div style={{ fontSize: '0.85rem', color: '#9e9eb0', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  {isLoading && <div className="spinner cyan"></div>}
                  {statusText}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Right Output Panel */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          
          {/* Tech Profile Summary Cards */}
          {techProfile && (
            <div className="glass-panel" style={{ padding: '1.5rem' }}>
              <h3 className="form-title" style={{ fontSize: '1.1rem', marginBottom: '1rem' }}>📊 Execution Profile: {projectName}</h3>
              <div className="stats-grid">
                <div className="stat-card">
                  <span className="stat-label">Language</span>
                  <span className="stat-value">{techProfile.primary_language}</span>
                </div>
                <div className="stat-card">
                  <span className="stat-label">Framework</span>
                  <span className="stat-value">{techProfile.framework || 'None'}</span>
                </div>
                <div className="stat-card">
                  <span className="stat-label">Scanned Files</span>
                  <span className="stat-value">{techProfile.files_scanned}</span>
                </div>
                <div className="stat-card">
                  <span className="stat-label">Build Duration</span>
                  <span className="stat-value">{executionTime}s</span>
                </div>
              </div>
              {savedPath && (
                <p style={{ marginTop: '1rem', fontSize: '0.8rem', color: '#00e676' }}>
                  [OK] Saved locally to: {savedPath}
                </p>
              )}
            </div>
          )}

          {/* Error Message Alert */}
          {errorMessage && (
            <div className="glass-panel" style={{ borderLeft: '4px solid #ff1744', background: 'rgba(255,23,68,0.03)' }}>
              <h4 style={{ color: '#ff1744', marginBottom: '0.5rem' }}>⚠ Error Occurred</h4>
              <p style={{ fontSize: '0.9rem', color: '#f5f5f7', whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                {errorMessage}
              </p>
            </div>
          )}

          {/* Preview Workspace */}
          {readmeContent ? (
            <div className="workspace-grid">
              
              {/* Raw Editor Pane */}
              <div className="pane-container">
                <div className="pane-header">
                  <span className="pane-title">Markdown Editor</span>
                  <div style={{ display: 'flex', gap: '0.5rem' }}>
                    <button className="action-btn" onClick={handleCopy}>Copy</button>
                    <button className="action-btn primary-btn" onClick={handleDownload}>Download</button>
                  </div>
                </div>
                <textarea
                  className="editor-textarea"
                  value={readmeContent}
                  onChange={(e) => setReadmeContent(e.target.value)}
                />
              </div>

              {/* Renders HTML Preview Pane */}
              <div className="pane-container">
                <div className="pane-header">
                  <span className="pane-title">Live Preview</span>
                </div>
                <div 
                  className="preview-body"
                  dangerouslySetInnerHTML={{ __html: marked.parse(readmeContent) }}
                />
              </div>

            </div>
          ) : (
            !isLoading && !errorMessage && (
              <div className="glass-panel" style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: '400px', textAlign: 'center', gap: '1rem' }}>
                <div style={{ fontSize: '3rem' }}>📝</div>
                <h3 style={{ fontSize: '1.4rem' }}>No Repository Scanned Yet</h3>
                <p style={{ color: '#9e9eb0', maxWidth: '400px', fontSize: '0.9rem' }}>
                  Input a local folder path or standard public GitHub repository URL on the left side to trigger our multi-agent assistant.
                </p>
              </div>
            )
          )}
        </div>
      </div>
    </div>
  );
}

export default App;
