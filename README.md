# ICM Flow Agents - Multi-Agent Incident Management System

## Overview
Enterprise-grade multi-agent system for automated incident management using Microsoft Agent Framework (2025), Azure AI Foundry, and GPT-5.2.

## Architecture

### System Components

#### 1. Input Layer
- **Raw Incident Data**: Ingests emails, chats, logs
- **Context Manager**: Manages session context and state
- **Tool Router**: Routes incidents to appropriate agents

#### 2. Processing & Orchestration
- **Summarizer Agent**: Normalizes and categorizes incidents
- **Supervisor Agent**: Central orchestrator for validation and delegation
- **Aggregated Results Layer**: Structures outputs for downstream processing

#### 3. Safety & Governance
- **AI Governance**: PII redaction, data control, guardrails
- **Responsible AI**: Prompt injection detection, jailbreak prevention
- **Memory Manager**: Short/long-term memory with stage management
- **Vector Store**: Semantic embeddings for context retrieval

#### 4. Specialized Workflow Agents
- **WF-5 Noise Agent**: Filters false positives and noise
- **WF-10 Impact Agent**: Assesses incident severity and impact
- **WF-25 Mitigation Agent**: Orchestrates mitigation strategies

#### 5. Observability & Control
- Error handling, run history, health checks, cost control

#### 6. Output Layer
- Filtered timelines, impact summaries, mitigation action plans

## Technology Stack

- **Framework**: Microsoft Agent Framework (2025) - v1.0.0b260130
- **LLM**: GPT-5.2 & GPT-5.2-Chat via Azure AI Foundry
- **Platform**: Azure AI Foundry (Microsoft Foundry)
- **Language**: Python 3.11+
- **Vector Store**: Azure AI Search
- **Memory**: Azure Cosmos DB
- **Monitoring**: Azure Application Insights
- **Deployment**: Azure Container Apps / Foundry Agent Service

## Prerequisites

- Python 3.11 or higher
- Azure subscription with AI Foundry access
- Azure AI Foundry project and resources
- GPT-5.2 model deployment

## Installation

```bash
# Install UV package manager (recommended)
pip install uv

# Install Microsoft Agent Framework
pip install agent-framework --pre

# Install additional dependencies
pip install -r requirements.txt
```

## Configuration

Create a `.env` file with your Azure credentials:

```env
AZURE_OPENAI_ENDPOINT=https://your-foundry-endpoint.azure.com
AZURE_OPENAI_API_KEY=your-api-key
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-5-2
AZURE_AI_SEARCH_ENDPOINT=https://your-search-endpoint.search.windows.net
AZURE_AI_SEARCH_KEY=your-search-key
AZURE_COSMOS_CONNECTION_STRING=your-cosmos-connection-string
```

## Project Structure

```
icm-flow-agents-cur/
├── src/
│   ├── agents/              # Agent implementations
│   │   ├── supervisor.py    # Supervisor Agent
│   │   ├── summarizer.py    # Summarizer Agent
│   │   ├── noise_agent.py   # WF-5 Noise Agent
│   │   ├── impact_agent.py  # WF-10 Impact Agent
│   │   └── mitigation_agent.py  # WF-25 Mitigation Agent
│   ├── core/                # Core infrastructure
│   │   ├── context_manager.py
│   │   ├── tool_router.py
│   │   ├── memory_manager.py
│   │   └── vector_store.py
│   ├── governance/          # Safety & governance
│   │   ├── ai_governance.py
│   │   ├── guardrails.py
│   │   └── pii_redaction.py
│   ├── input/               # Input layer
│   │   ├── data_ingestion.py
│   │   └── parsers.py
│   ├── output/              # Output layer
│   │   ├── evaluator.py
│   │   └── formatters.py
│   ├── observability/       # Monitoring & control
│   │   ├── error_handler.py
│   │   ├── health_check.py
│   │   └── cost_tracker.py
│   └── config/              # Configuration
│       ├── settings.py
│       └── prompts.py
├── tests/                   # Test suite
├── docs/                    # Documentation
├── deployment/              # Deployment configs
├── requirements.txt
├── pyproject.toml
└── README.md
```

## Usage

```python
from src.agents.supervisor import SupervisorAgent
from src.core.context_manager import ContextManager

# Initialize the system
context_manager = ContextManager()
supervisor = SupervisorAgent()

# Process an incident
incident_data = {
    "source": "email",
    "content": "Production database is down...",
    "timestamp": "2026-02-10T10:00:00Z"
}

result = await supervisor.process_incident(incident_data)
print(result)
```

## Development

```bash
# Run tests
pytest tests/

# Run with development server
python -m src.main

# Format code
black src/
ruff check src/
```

## Deployment

### Option 1: Azure Container Apps
```bash
az containerapp up --name icm-flow-agents --resource-group <rg-name>
```

### Option 2: Foundry Agent Service (Hosted Agents)
Deploy directly through Azure AI Foundry portal with managed infrastructure.

## License

MIT License

## Contributing

See CONTRIBUTING.md for guidelines.

<!-- Added detailed architecture references -->

<!-- Added detailed architecture references -->
