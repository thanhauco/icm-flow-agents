# Agent Specifications - Detailed Design

## Table of Contents
1. [Supervisor Agent](#supervisor-agent)
2. [Summarizer Agent](#summarizer-agent)
3. [Noise Agent (WF-5)](#noise-agent-wf-5)
4. [Impact Agent (WF-10)](#impact-agent-wf-10)
5. [Mitigation Agent (WF-25)](#mitigation-agent-wf-25)

---

## Supervisor Agent

### Overview
The Supervisor Agent is the central orchestrator responsible for coordinating all specialized agents, managing workflow state, and ensuring quality outcomes.

### Architecture

```mermaid
graph TB
    subgraph SupervisorCore["👔 SUPERVISOR AGENT CORE"]
        direction TB
        
        subgraph InputValidation["📥 Input Validation"]
            SchemaCheck["✅ Schema Check"]
            DataQuality["🔍 Data Quality"]
            SecurityCheck["🔒 Security Check"]
        end
        
        subgraph WorkflowPlanning["📋 Workflow Planning"]
            IncidentAnalysis["🔍 Incident Analysis"]
            AgentSelection["🎯 Agent Selection"]
            ExecutionPlan["📝 Execution Plan"]
            PriorityQueue["⚡ Priority Queue"]
        end
        
        subgraph Delegation["🎯 Delegation Engine"]
            TaskDistribution["📤 Task Distribution"]
            ParallelExecution["⚡ Parallel Execution"]
            SequentialExecution["➡️ Sequential Execution"]
        end
        
        subgraph Monitoring["👀 Monitoring & Control"]
            ProgressTracking["📊 Progress Tracking"]
            ErrorDetection["❌ Error Detection"]
            TimeoutManagement["⏱️ Timeout Management"]
            CircuitBreaker["🔌 Circuit Breaker"]
        end
        
        subgraph Aggregation["📊 Result Aggregation"]
            ResultCollection["📥 Result Collection"]
            Deduplication["🔄 Deduplication"]
            Synthesis["🧩 Synthesis"]
            QualityAssurance["✅ Quality Assurance"]
        end
    end
    
    subgraph ExternalSystems["🔗 External Systems"]
        MemoryStore["💾 Memory Store"]
        VectorDB["🔍 Vector DB"]
        LLM["🤖 GPT-5.2-Chat"]
        Telemetry["📊 Telemetry"]
    end
    
    InputValidation --> WorkflowPlanning
    WorkflowPlanning --> Delegation
    Delegation --> Monitoring
    Monitoring --> Aggregation
    
    WorkflowPlanning -.-> MemoryStore
    WorkflowPlanning -.-> VectorDB
    WorkflowPlanning -.-> LLM
    
    Monitoring -.-> Telemetry
    Aggregation -.-> MemoryStore

    style SupervisorCore fill:#9B59B6,stroke:#8E44AD,stroke-width:3px,color:#fff
    style InputValidation fill:#3498DB,stroke:#2874A6,stroke-width:2px,color:#fff
    style WorkflowPlanning fill:#2ECC71,stroke:#27AE60,stroke-width:2px,color:#fff
    style Delegation fill:#F39C12,stroke:#E67E22,stroke-width:2px,color:#fff
    style Monitoring fill:#E74C3C,stroke:#C0392B,stroke-width:2px,color:#fff
    style Aggregation fill:#1ABC9C,stroke:#16A085,stroke-width:2px,color:#fff
    style ExternalSystems fill:#95A5A6,stroke:#7F8C8D,stroke-width:2px,color:#fff
```

### State Machine

```mermaid
stateDiagram-v2
    [*] --> Idle
    Idle --> Validating: Receive Incident
    Validating --> Planning: Valid
    Validating --> Failed: Invalid
    Planning --> Delegating: Plan Ready
    Delegating --> Monitoring: Agents Started
    Monitoring --> Monitoring: Progress Update
    Monitoring --> Aggregating: All Complete
    Monitoring --> Failed: Timeout/Error
    Aggregating --> Completed: Success
    Aggregating --> Failed: Quality Check Failed
    Completed --> [*]
    Failed --> [*]
    
    note right of Planning
        LLM determines optimal
        workflow strategy
    end note
    
    note right of Monitoring
        Track agent progress,
        handle failures
    end note
```

### Decision Logic

```mermaid
flowchart TD
    Start([Receive Incident]) --> Validate{Valid?}
    Validate -->|No| Reject[Reject Incident]
    Validate -->|Yes| Analyze[Analyze Incident Type]
    
    Analyze --> CheckNoise{Potential<br/>Noise?}
    CheckNoise -->|Yes| NoiseAgent[Route to Noise Agent]
    CheckNoise -->|No| CheckSeverity{High<br/>Severity?}
    
    CheckSeverity -->|Yes| ImpactAgent[Route to Impact Agent]
    CheckSeverity -->|No| CheckMitigation{Needs<br/>Mitigation?}
    
    CheckMitigation -->|Yes| MitigationAgent[Route to Mitigation Agent]
    CheckMitigation -->|No| DirectOutput[Direct to Output]
    
    NoiseAgent --> IsNoise{Is Noise?}
    IsNoise -->|Yes| Filter[Filter Out]
    IsNoise -->|No| ImpactAgent
    
    ImpactAgent --> Severity{Severity<br/>Level?}
    Severity -->|P0/P1| UrgentMitigation[Urgent Mitigation]
    Severity -->|P2/P3| MitigationAgent
    Severity -->|P4| Monitor[Monitor Only]
    
    UrgentMitigation --> Aggregate[Aggregate Results]
    MitigationAgent --> Aggregate
    Monitor --> Aggregate
    DirectOutput --> Aggregate
    Filter --> End([End])
    
    Aggregate --> QA{Quality<br/>Check?}
    QA -->|Pass| Output[Output Results]
    QA -->|Fail| Retry{Retry<br/>Count?}
    Retry -->|< 3| Analyze
    Retry -->|>= 3| Escalate[Escalate to Human]
    
    Output --> End
    Escalate --> End
    Reject --> End

    style Start fill:#2ECC71,stroke:#27AE60,stroke-width:2px,color:#fff
    style End fill:#E74C3C,stroke:#C0392B,stroke-width:2px,color:#fff
    style NoiseAgent fill:#27AE60,stroke:#229954,stroke-width:2px,color:#fff
    style ImpactAgent fill:#F39C12,stroke:#E67E22,stroke-width:2px,color:#fff
    style MitigationAgent fill:#3498DB,stroke:#2874A6,stroke-width:2px,color:#fff
```

### Prompt Template

```python
SUPERVISOR_SYSTEM_PROMPT = """
You are the Supervisor Agent in an enterprise incident management system.

Your responsibilities:
1. Validate incoming incidents for completeness and quality
2. Analyze incident characteristics to determine optimal workflow
3. Delegate tasks to specialized agents (Noise, Impact, Mitigation)
4. Monitor agent execution and handle failures
5. Aggregate results and ensure quality

Decision criteria:
- Route to Noise Agent if: Recurring pattern, low severity, no user impact
- Route to Impact Agent if: High severity, multiple services affected, user impact
- Route to Mitigation Agent if: Requires action plan, automation available

Always provide clear reasoning for your decisions.
"""

SUPERVISOR_USER_PROMPT = """
Incident Details:
{incident_json}

Historical Context:
{similar_incidents}

Current System State:
{system_state}

Task: Analyze this incident and determine the optimal workflow strategy.
Provide your decision in JSON format with reasoning.
"""
```

### Key Methods

```python
class SupervisorAgent:
    async def process_incident(self, incident: Incident) -> SupervisorResult:
        """Main entry point for incident processing"""
        
    async def validate_incident(self, incident: Incident) -> ValidationResult:
        """Validate incident data quality and security"""
        
    async def plan_workflow(self, incident: Incident) -> WorkflowPlan:
        """Determine optimal agent workflow using LLM"""
        
    async def delegate_to_agents(self, plan: WorkflowPlan) -> List[AgentTask]:
        """Distribute tasks to specialized agents"""
        
    async def monitor_execution(self, tasks: List[AgentTask]) -> ExecutionStatus:
        """Track agent progress and handle failures"""
        
    async def aggregate_results(self, results: List[AgentResult]) -> AggregatedResult:
        """Combine and synthesize agent outputs"""
```

---

## Summarizer Agent

### Overview
The Summarizer Agent transforms raw, unstructured incident data into normalized, structured format suitable for downstream processing.

### Processing Pipeline

```mermaid
graph LR
    subgraph Input["📥 Input"]
        RawText["📄 Raw Text<br/>Unstructured"]
        Metadata["📋 Metadata<br/>Source, Timestamp"]
    end
    
    subgraph Extraction["🔍 Information Extraction"]
        direction TB
        TitleExtract["📌 Title Extraction"]
        DescExtract["📝 Description Extraction"]
        ServiceExtract["🔧 Service Identification"]
        ErrorExtract["❌ Error Pattern Extraction"]
        TimeExtract["⏰ Timestamp Extraction"]
    end
    
    subgraph Categorization["🏷️ Categorization"]
        direction TB
        TypeClassify["🎯 Type Classification<br/>Outage/Degradation/Security"]
        SeverityEstimate["⚡ Severity Estimation<br/>P0-P4"]
        ComponentMap["🗺️ Component Mapping<br/>Service Dependencies"]
    end
    
    subgraph Normalization["⚖️ Normalization"]
        direction TB
        SchemaMap["📐 Schema Mapping"]
        DataClean["🧹 Data Cleaning"]
        Validation["✅ Validation"]
    end
    
    subgraph Enrichment["✨ Enrichment"]
        direction TB
        HistoricalLookup["🔍 Historical Lookup<br/>Similar Incidents"]
        ContextAdd["🧠 Context Addition<br/>Service Health"]
        TagGeneration["🏷️ Tag Generation<br/>Auto-tagging"]
    end
    
    subgraph Output["📤 Output"]
        StructuredIncident["📊 Structured Incident<br/>JSON Schema"]
    end
    
    RawText --> TitleExtract
    Metadata --> TitleExtract
    
    TitleExtract --> DescExtract
    DescExtract --> ServiceExtract
    ServiceExtract --> ErrorExtract
    ErrorExtract --> TimeExtract
    
    TimeExtract --> TypeClassify
    TypeClassify --> SeverityEstimate
    SeverityEstimate --> ComponentMap
    
    ComponentMap --> SchemaMap
    SchemaMap --> DataClean
    DataClean --> Validation
    
    Validation --> HistoricalLookup
    HistoricalLookup --> ContextAdd
    ContextAdd --> TagGeneration
    
    TagGeneration --> StructuredIncident

    style Input fill:#E74C3C,stroke:#C0392B,stroke-width:2px,color:#fff
    style Extraction fill:#3498DB,stroke:#2874A6,stroke-width:2px,color:#fff
    style Categorization fill:#F39C12,stroke:#E67E22,stroke-width:2px,color:#fff
    style Normalization fill:#9B59B6,stroke:#8E44AD,stroke-width:2px,color:#fff
    style Enrichment fill:#1ABC9C,stroke:#16A085,stroke-width:2px,color:#fff
    style Output fill:#2ECC71,stroke:#27AE60,stroke-width:2px,color:#fff
```

### Categorization Logic

```mermaid
graph TD
    Start([Raw Incident]) --> ExtractKeywords[Extract Keywords]
    
    ExtractKeywords --> CheckType{Check Type}
    
    CheckType -->|down, outage, unavailable| Outage[Type: Outage]
    CheckType -->|slow, latency, timeout| Degradation[Type: Degradation]
    CheckType -->|unauthorized, breach, attack| Security[Type: Security]
    CheckType -->|error, exception, failed| Error[Type: Error]
    CheckType -->|warning, alert| Warning[Type: Warning]
    
    Outage --> SevOutage{Impact Scope}
    Degradation --> SevDeg{Performance Drop}
    Security --> SevSec{Data Exposure}
    Error --> SevErr{Error Rate}
    Warning --> SevWarn{Threshold}
    
    SevOutage -->|All services| P0
    SevOutage -->|Critical service| P1
    SevOutage -->|Single service| P2
    
    SevDeg -->|> 50% degradation| P1
    SevDeg -->|20-50% degradation| P2
    SevDeg -->|< 20% degradation| P3
    
    SevSec -->|Customer data| P0
    SevSec -->|Internal data| P1
    SevSec -->|Metadata only| P2
    
    SevErr -->|> 10% error rate| P1
    SevErr -->|1-10% error rate| P2
    SevErr -->|< 1% error rate| P3
    
    SevWarn -->|Critical threshold| P2
    SevWarn -->|Warning threshold| P3
    SevWarn -->|Info threshold| P4
    
    P0 --> Output([Categorized Incident])
    P1 --> Output
    P2 --> Output
    P3 --> Output
    P4 --> Output

    style Start fill:#2ECC71,stroke:#27AE60,stroke-width:2px,color:#fff
    style Output fill:#2ECC71,stroke:#27AE60,stroke-width:2px,color:#fff
    style P0 fill:#E74C3C,stroke:#C0392B,stroke-width:2px,color:#fff
    style P1 fill:#F39C12,stroke:#E67E22,stroke-width:2px,color:#fff
    style P2 fill:#F1C40F,stroke:#F39C12,stroke-width:2px,color:#333
    style P3 fill:#3498DB,stroke:#2874A6,stroke-width:2px,color:#fff
    style P4 fill:#95A5A6,stroke:#7F8C8D,stroke-width:2px,color:#fff
```

### Output Schema

```json
{
  "incident_id": "INC-2026-001234",
  "version": "1.0",
  "timestamp": "2026-02-10T10:00:00Z",
  "source": {
    "type": "email",
    "channel": "alerts@company.com",
    "original_id": "email-12345"
  },
  "classification": {
    "type": "outage",
    "category": "infrastructure",
    "subcategory": "database",
    "severity": "P1",
    "confidence": 0.92
  },
  "content": {
    "title": "Production Database Connection Timeout",
    "description": "Users unable to access application due to database connection failures",
    "affected_services": ["api-gateway", "user-service", "payment-service"],
    "error_patterns": ["ConnectionTimeout", "PoolExhausted"],
    "keywords": ["database", "timeout", "connection", "production"]
  },
  "metadata": {
    "environment": "production",
    "region": "us-west-2",
    "customer_impact": "high",
    "estimated_affected_users": 15000,
    "tags": ["database", "connectivity", "urgent"]
  },
  "enrichment": {
    "similar_incidents": ["INC-2026-001100", "INC-2025-098765"],
    "historical_resolution_time_avg": "45 minutes",
    "common_root_causes": ["connection pool exhaustion", "network issue"]
  }
}
```

---

## Noise Agent (WF-5)

### Overview
The Noise Agent filters false positives and non-actionable alerts from the incident stream.

### Detection Algorithm

```mermaid
graph TB
    subgraph Input["📥 Input"]
        Incident["🔴 Incident"]
    end
    
    subgraph FeatureExtraction["🔍 Feature Extraction"]
        direction TB
        PatternExtract["🔄 Pattern Extraction<br/>Recurring Signatures"]
        FrequencyAnalysis["📊 Frequency Analysis<br/>Time Series"]
        ServiceContext["🔧 Service Context<br/>Known Issues"]
        UserFeedback["👥 User Feedback<br/>Historical Labels"]
    end
    
    subgraph VectorSearch["🔍 Vector Search"]
        direction TB
        EmbedIncident["📊 Embed Incident<br/>text-embedding-3-large"]
        SearchSimilar["🔎 Search Similar<br/>Cosine Similarity"]
        RankResults["📈 Rank Results<br/>Top-K Matches"]
    end
    
    subgraph Classification["🏷️ Classification"]
        direction TB
        RuleBasedCheck["📋 Rule-based Check<br/>Known Noise Patterns"]
        LLMClassification["🤖 LLM Classification<br/>GPT-5.2 Analysis"]
        EnsembleVote["🗳️ Ensemble Vote<br/>Combine Signals"]
    end
    
    subgraph Scoring["📊 Noise Scoring"]
        direction TB
        HistoricalScore["📜 Historical Score<br/>40% weight"]
        SimilarityScore["🔄 Similarity Score<br/>30% weight"]
        FrequencyScore["⏰ Frequency Score<br/>20% weight"]
        FeedbackScore["👥 Feedback Score<br/>10% weight"]
        FinalScore["🎯 Final Noise Score<br/>0-100"]
    end
    
    subgraph Decision["✅ Decision"]
        direction TB
        Threshold{Score > 70?}
        Filter["🔇 Filter<br/>Mark as Noise"]
        Escalate["⚡ Escalate<br/>Pass to Impact Agent"]
    end
    
    subgraph Output["📤 Output"]
        Result["📋 Noise Result<br/>Decision + Reasoning"]
    end
    
    Incident --> PatternExtract
    PatternExtract --> FrequencyAnalysis
    FrequencyAnalysis --> ServiceContext
    ServiceContext --> UserFeedback
    
    UserFeedback --> EmbedIncident
    EmbedIncident --> SearchSimilar
    SearchSimilar --> RankResults
    
    RankResults --> RuleBasedCheck
    RankResults --> LLMClassification
    
    RuleBasedCheck --> EnsembleVote
    LLMClassification --> EnsembleVote
    
    EnsembleVote --> HistoricalScore
    HistoricalScore --> SimilarityScore
    SimilarityScore --> FrequencyScore
    FrequencyScore --> FeedbackScore
    FeedbackScore --> FinalScore
    
    FinalScore --> Threshold
    Threshold -->|Yes| Filter
    Threshold -->|No| Escalate
    
    Filter --> Result
    Escalate --> Result

    style Input fill:#E74C3C,stroke:#C0392B,stroke-width:2px,color:#fff
    style FeatureExtraction fill:#3498DB,stroke:#2874A6,stroke-width:2px,color:#fff
    style VectorSearch fill:#9B59B6,stroke:#8E44AD,stroke-width:2px,color:#fff
    style Classification fill:#F39C12,stroke:#E67E22,stroke-width:2px,color:#fff
    style Scoring fill:#1ABC9C,stroke:#16A085,stroke-width:2px,color:#fff
    style Decision fill:#E67E22,stroke:#D35400,stroke-width:2px,color:#fff
    style Output fill:#2ECC71,stroke:#27AE60,stroke-width:2px,color:#fff
```

### Noise Patterns

Common noise patterns automatically detected:

| Pattern Type | Example | Detection Method |
|-------------|---------|------------------|
| **Flapping Alerts** | Service up/down every 5 min | Frequency analysis |
| **Test Alerts** | "TEST" in title | Keyword matching |
| **Duplicate Alerts** | Same error, different timestamp | Deduplication |
| **Known Issues** | Documented non-issues | Knowledge base lookup |
| **Low Impact** | Single user, non-critical service | Impact scoring |
| **Auto-resolved** | Resolved within 1 minute | Time-to-resolution |

### Confidence Calibration

```mermaid
graph LR
    subgraph LowConfidence["🟡 Low Confidence (0-60)"]
        LC1["Ambiguous patterns"]
        LC2["Limited historical data"]
        LC3["Conflicting signals"]
    end
    
    subgraph MediumConfidence["🟠 Medium Confidence (60-80)"]
        MC1["Some historical matches"]
        MC2["Moderate frequency"]
        MC3["Partial pattern match"]
    end
    
    subgraph HighConfidence["🟢 High Confidence (80-100)"]
        HC1["Strong historical evidence"]
        HC2["Clear noise pattern"]
        HC3["High similarity to known noise"]
    end
    
    LowConfidence --> Action1[Human Review Required]
    MediumConfidence --> Action2[Soft Filter + Monitor]
    HighConfidence --> Action3[Auto-filter]

    style LowConfidence fill:#F1C40F,stroke:#F39C12,stroke-width:2px,color:#333
    style MediumConfidence fill:#F39C12,stroke:#E67E22,stroke-width:2px,color:#fff
    style HighConfidence fill:#2ECC71,stroke:#27AE60,stroke-width:2px,color:#fff
```

---

## Impact Agent (WF-10)

### Overview
The Impact Agent assesses incident severity and customer impact across multiple dimensions.

### Impact Assessment Framework

```mermaid
graph TB
    subgraph Input["📥 Input"]
        ValidatedIncident["🟢 Validated Incident"]
    end
    
    subgraph ScopeAnalysis["🌍 Scope Analysis"]
        direction TB
        ServiceMap["🗺️ Service Mapping<br/>Dependency Graph"]
        AffectedServices["🔧 Affected Services<br/>Direct + Indirect"]
        GeographicSpread["🌐 Geographic Spread<br/>Regional Impact"]
    end
    
    subgraph SeverityCalculation["⚡ Severity Calculation"]
        direction TB
        ErrorRate["📊 Error Rate<br/>% Failed Requests"]
        Latency["⏱️ Latency Impact<br/>P50, P95, P99"]
        Availability["💚 Availability<br/>Uptime %"]
        Throughput["📈 Throughput<br/>RPS Drop"]
    end
    
    subgraph UserImpact["👥 User Impact"]
        direction TB
        AffectedUsers["👤 Affected Users<br/>Count Estimation"]
        UserSegment["🎯 User Segment<br/>Free/Premium/Enterprise"]
        BusinessCriticality["💼 Business Criticality<br/>Revenue Impact"]
    end
    
    subgraph BusinessImpact["💰 Business Impact"]
        direction TB
        RevenueImpact["💵 Revenue Impact<br/>$/hour"]
        SLABreach["📋 SLA Breach<br/>Contract Risk"]
        ReputationRisk["⭐ Reputation Risk<br/>Brand Impact"]
    end
    
    subgraph TimeAnalysis["⏰ Time Analysis"]
        direction TB
        TimeToDetect["🔍 Time to Detect<br/>MTTD"]
        EstimatedTTR["🔧 Estimated TTR<br/>MTTR Prediction"]
        DurationImpact["⏳ Duration Impact<br/>Cumulative Effect"]
    end
    
    subgraph Aggregation["📊 Impact Aggregation"]
        direction TB
        WeightedScore["⚖️ Weighted Score<br/>Multi-dimensional"]
        PriorityLevel["🎯 Priority Level<br/>P0-P4"]
        ConfidenceInterval["📈 Confidence Interval<br/>95% CI"]
    end
    
    subgraph Output["📤 Output"]
        ImpactReport["📊 Impact Report<br/>Comprehensive Summary"]
    end
    
    ValidatedIncident --> ServiceMap
    ServiceMap --> AffectedServices
    AffectedServices --> GeographicSpread
    
    GeographicSpread --> ErrorRate
    ErrorRate --> Latency
    Latency --> Availability
    Availability --> Throughput
    
    Throughput --> AffectedUsers
    AffectedUsers --> UserSegment
    UserSegment --> BusinessCriticality
    
    BusinessCriticality --> RevenueImpact
    RevenueImpact --> SLABreach
    SLABreach --> ReputationRisk
    
    ReputationRisk --> TimeToDetect
    TimeToDetect --> EstimatedTTR
    EstimatedTTR --> DurationImpact
    
    DurationImpact --> WeightedScore
    WeightedScore --> PriorityLevel
    PriorityLevel --> ConfidenceInterval
    
    ConfidenceInterval --> ImpactReport

    style Input fill:#2ECC71,stroke:#27AE60,stroke-width:2px,color:#fff
    style ScopeAnalysis fill:#3498DB,stroke:#2874A6,stroke-width:2px,color:#fff
    style SeverityCalculation fill:#E74C3C,stroke:#C0392B,stroke-width:2px,color:#fff
    style UserImpact fill:#9B59B6,stroke:#8E44AD,stroke-width:2px,color:#fff
    style BusinessImpact fill:#F39C12,stroke:#E67E22,stroke-width:2px,color:#fff
    style TimeAnalysis fill:#1ABC9C,stroke:#16A085,stroke-width:2px,color:#fff
    style Aggregation fill:#E67E22,stroke:#D35400,stroke-width:2px,color:#fff
    style Output fill:#2ECC71,stroke:#27AE60,stroke-width:2px,color:#fff
```

### Severity Matrix

```mermaid
graph TD
    subgraph Matrix["📊 Severity Decision Matrix"]
        Start([Incident]) --> CheckAvailability{Availability<br/>Impact?}
        
        CheckAvailability -->|Complete Outage| CheckScope1{Scope?}
        CheckAvailability -->|Partial Outage| CheckScope2{Scope?}
        CheckAvailability -->|Degradation| CheckScope3{Scope?}
        CheckAvailability -->|No Impact| P4
        
        CheckScope1 -->|All Services| P0_Critical[P0 - CRITICAL<br/>Complete Outage]
        CheckScope1 -->|Critical Service| P1_High1[P1 - HIGH<br/>Critical Service Down]
        CheckScope1 -->|Single Service| P2_Medium1[P2 - MEDIUM<br/>Service Outage]
        
        CheckScope2 -->|> 50% Users| P1_High2[P1 - HIGH<br/>Major Partial Outage]
        CheckScope2 -->|10-50% Users| P2_Medium2[P2 - MEDIUM<br/>Partial Outage]
        CheckScope2 -->|< 10% Users| P3_Low1[P3 - LOW<br/>Minor Outage]
        
        CheckScope3 -->|> 50% Degradation| P2_Medium3[P2 - MEDIUM<br/>Severe Degradation]
        CheckScope3 -->|20-50% Degradation| P3_Low2[P3 - LOW<br/>Moderate Degradation]
        CheckScope3 -->|< 20% Degradation| P4_Info[P4 - INFO<br/>Minor Degradation]
    end

    style Start fill:#2ECC71,stroke:#27AE60,stroke-width:2px,color:#fff
    style P0_Critical fill:#C0392B,stroke:#922B21,stroke-width:3px,color:#fff
    style P1_High1 fill:#E74C3C,stroke:#C0392B,stroke-width:2px,color:#fff
    style P1_High2 fill:#E74C3C,stroke:#C0392B,stroke-width:2px,color:#fff
    style P2_Medium1 fill:#F39C12,stroke:#E67E22,stroke-width:2px,color:#fff
    style P2_Medium2 fill:#F39C12,stroke:#E67E22,stroke-width:2px,color:#fff
    style P2_Medium3 fill:#F39C12,stroke:#E67E22,stroke-width:2px,color:#fff
    style P3_Low1 fill:#3498DB,stroke:#2874A6,stroke-width:2px,color:#fff
    style P3_Low2 fill:#3498DB,stroke:#2874A6,stroke-width:2px,color:#fff
    style P4 fill:#95A5A6,stroke:#7F8C8D,stroke-width:2px,color:#fff
    style P4_Info fill:#95A5A6,stroke:#7F8C8D,stroke-width:2px,color:#fff
```

---

## Mitigation Agent (WF-25)

### Overview
The Mitigation Agent generates actionable remediation plans and orchestrates mitigation workflows.

### Mitigation Strategy

```mermaid
graph TB
    subgraph Input["📥 Input"]
        ImpactReport["📊 Impact Report"]
    end
    
    subgraph RootCauseAnalysis["🔍 Root Cause Analysis"]
        direction TB
        HypothesisGen["💡 Hypothesis Generation<br/>LLM-powered"]
        EvidenceGather["📊 Evidence Gathering<br/>Logs, Metrics"]
        CauseRanking["📈 Cause Ranking<br/>Probability Scoring"]
    end
    
    subgraph PlaybookRetrieval["📚 Playbook Retrieval"]
        direction TB
        SearchKB["🔎 Search Knowledge Base<br/>Vector Search"]
        MatchPlaybooks["📖 Match Playbooks<br/>Similar Incidents"]
        AdaptSolutions["🔄 Adapt Solutions<br/>Context-aware"]
    end
    
    subgraph PlanGeneration["📝 Plan Generation"]
        direction TB
        ImmediateActions["⚡ Immediate Actions<br/>0-15 min"]
        ShortTermActions["🔧 Short-term Actions<br/>15-60 min"]
        LongTermActions["📋 Long-term Actions<br/>1+ hours"]
    end
    
    subgraph ActionPrioritization["⚡ Action Prioritization"]
        direction TB
        ImpactScore["📊 Impact Score<br/>Expected Benefit"]
        EffortEstimate["⏱️ Effort Estimate<br/>Time Required"]
        RiskAssessment["⚠️ Risk Assessment<br/>Failure Probability"]
        Priority["🎯 Priority Ranking<br/>ROI-based"]
    end
    
    subgraph AutomationCheck["🤖 Automation Check"]
        direction TB
        RunbookAvailable{"Runbook<br/>Available?"}
        SafetyCheck["🔒 Safety Check<br/>Approval Required?"]
        AutoExecute["⚡ Auto-execute<br/>With Monitoring"]
        ManualStep["👤 Manual Step<br/>Human Required"]
    end
    
    subgraph Output["📤 Output"]
        MitigationPlan["📝 Mitigation Plan<br/>Action Plan"]
    end
    
    ImpactReport --> HypothesisGen
    HypothesisGen --> EvidenceGather
    EvidenceGather --> CauseRanking
    
    CauseRanking --> SearchKB
    SearchKB --> MatchPlaybooks
    MatchPlaybooks --> AdaptSolutions
    
    AdaptSolutions --> ImmediateActions
    ImmediateActions --> ShortTermActions
    ShortTermActions --> LongTermActions
    
    LongTermActions --> ImpactScore
    ImpactScore --> EffortEstimate
    EffortEstimate --> RiskAssessment
    RiskAssessment --> Priority
    
    Priority --> RunbookAvailable
    RunbookAvailable -->|Yes| SafetyCheck
    RunbookAvailable -->|No| ManualStep
    SafetyCheck -->|Safe| AutoExecute
    SafetyCheck -->|Risky| ManualStep
    
    AutoExecute --> MitigationPlan
    ManualStep --> MitigationPlan

    style Input fill:#2ECC71,stroke:#27AE60,stroke-width:2px,color:#fff
    style RootCauseAnalysis fill:#9B59B6,stroke:#8E44AD,stroke-width:2px,color:#fff
    style PlaybookRetrieval fill:#3498DB,stroke:#2874A6,stroke-width:2px,color:#fff
    style PlanGeneration fill:#F39C12,stroke:#E67E22,stroke-width:2px,color:#fff
    style ActionPrioritization fill:#1ABC9C,stroke:#16A085,stroke-width:2px,color:#fff
    style AutomationCheck fill:#E67E22,stroke:#D35400,stroke-width:2px,color:#fff
    style Output fill:#2ECC71,stroke:#27AE60,stroke-width:2px,color:#fff
```

### Action Timeline

```mermaid
gantt
    title Mitigation Action Timeline
    dateFormat  mm:ss
    axisFormat %M:%S
    
    section Immediate (0-15 min)
    Rollback Deployment           :crit, 00:00, 05:00
    Scale Up Resources            :crit, 00:00, 03:00
    Enable Circuit Breaker        :crit, 00:00, 02:00
    Alert On-call Team            :crit, 00:00, 01:00
    
    section Short-term (15-60 min)
    Apply Hotfix                  :active, 05:00, 20:00
    Reroute Traffic               :active, 03:00, 10:00
    Restart Services              :active, 05:00, 08:00
    Update Monitoring             :active, 10:00, 15:00
    
    section Long-term (1+ hours)
    Deploy Permanent Fix          :15:00, 30:00
    Update Documentation          :20:00, 20:00
    Post-mortem Analysis          :40:00, 40:00
    Implement Prevention          :60:00, 120:00
```

### Runbook Execution

```mermaid
sequenceDiagram
    participant MA as 🔧 Mitigation Agent
    participant KB as 📚 Knowledge Base
    participant Auto as 🤖 Automation Engine
    participant Approval as 👤 Approval System
    participant Infra as ☁️ Infrastructure
    participant Monitor as 📊 Monitoring
    
    MA->>KB: Search for runbook
    KB-->>MA: Return matching runbook
    
    MA->>MA: Adapt runbook to context
    MA->>Auto: Check automation availability
    Auto-->>MA: Runbook available
    
    MA->>MA: Assess risk level
    
    alt High Risk Action
        MA->>Approval: Request human approval
        Approval-->>MA: Approved
    end
    
    MA->>Auto: Execute runbook
    Auto->>Infra: Apply changes
    Infra-->>Auto: Execution status
    
    loop Monitor Progress
        Auto->>Monitor: Check metrics
        Monitor-->>Auto: Health status
        Auto->>MA: Progress update
    end
    
    Auto-->>MA: Execution complete
    MA->>Monitor: Verify resolution
    Monitor-->>MA: Incident resolved
```

---

**Document Version**: 1.0  
**Last Updated**: February 10, 2026  
**Author**: ICM Flow Agents Team
