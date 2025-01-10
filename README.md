# Sentinel AI Gateway

An enterprise security middleware designed to intercept, validate, and audit actions requested by autonomous AI agents. Built with FastAPI and wrapped in a native desktop interface via PyWebView, Sentinel acts as a Zero-Trust firewall for agentic workflows.

## Core Features

- **Threat Signature Matching:** Validates `AgentAction` payloads (READ, WRITE, EXECUTE, NETWORK) against a library of known malicious signatures.
- **MITRE ATLAS & NIST CSF 2.0 Mapping:** Every blocked action is categorized using official MITRE ATLAS and NIST CSF 2.0 frameworks (e.g., blocking `/etc/shadow` reads maps to `AML.T0006` and `PR.AC-4`).
- **Immutable Audit Logging:** All validation attempts (both `ALLOWED` and `BLOCKED`) are logged with timestamps to a local SQLite database (`sentinel_audit.db`).
- **Real-time Metrics Dashboard:** Provides a REST endpoint (`/api/v1/metrics`) to calculate block rates and view recent threat intelligence.
- **Desktop & API Modes:** Runs as a native desktop app using PyWebView or can be deployed headlessly as a FastAPI service.

## Architecture

- **Engine (`core/engine.py`):** The core validation logic and SQLite logger.
- **Threat Library (`core/mitre_mapping.py`):** Hardcoded security signatures mapping to MITRE/NIST.
- **API (`src/api.py`):** FastAPI routes for `/validate` and `/metrics`.
- **UI (`static/index.html`):** A dark-themed web dashboard for visualizing metrics.

## Example Blocked Action

If an agent attempts a destructive command, Sentinel intercepts it:

```json
// Request to POST /api/v1/validate
{
  "agent_id": "agent-007",
  "action_type": "EXECUTE",
  "target": "rm -rf /",
  "parameters": {}
}

// Sentinel Response (403 Forbidden)
{
  "status": "BLOCKED",
  "message": "Action blocked: Destructive filesystem wipe attempt",
  "threat_intel": {
    "MITRE_ATLAS": "AML.T0012 (Valid Accounts)",
    "NIST_CSF": "PR.AC-4 (Access Control)"
  }
}
```

## Setup & Installation

1. Clone the repository and install dependencies:
   ```bash
   git clone https://github.com/jafersathikbeta/Sentinel-AI-Gateway.git
   cd Sentinel-AI-Gateway
   pip install -r requirements.txt
   ```

2. Run the desktop application:
   ```bash
   python run.py
   ```

3. (Optional) Run as a headless API server:
   ```bash
   uvicorn src.api:app --host 127.0.0.1 --port 8000
   ``` 
 
 
 
