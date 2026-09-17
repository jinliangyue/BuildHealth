# BuildHealth Architecture

> System structure and data flow. Diagrams render on GitHub and in any
> Mermaid-capable viewer.
>
> Diagrams describe the current implementation. See
> `28_Project_Fact_Sheet.md` for the verified fact baseline.

---

## 1. System layers

```mermaid
flowchart TD
    UI["React + TypeScript SPA<br/>8 pages · ECharts"]
    API["FastAPI<br/>19 endpoints"]
    SVC["Service layer<br/>assessment · retrofit"]
    AN["Engineering Analytics<br/>anomaly · health · risk · priority · rules"]
    AI["AI layer<br/>providers · context builder · redlines"]
    KB["Knowledge retrieval<br/>loader · chunker · TF-IDF retriever"]
    DB[("SQLite<br/>8 tables")]

    UI -->|"HTTP /api"| API
    API --> SVC
    SVC --> AN
    SVC --> AI
    AI --> KB
    AN --> DB
    SVC --> DB
    KB -.->|"reads Markdown"| KB
```

The analytics engine does not depend on the API layer, and the AI layer does not
depend on the analytics internals — it reads a typed engineering context that
the service layer builds. This keeps the deterministic computation independent
of both the transport and the explanation layer.

---

## 2. Engineering data flow

```mermaid
flowchart TD
    B["Building<br/>asset record"]
    S["Sensor<br/>measurement point"]
    R["Monitoring Record<br/>timestamp · value · quality flag"]
    A["Anomaly Detection<br/>threshold · rate of change · z-score"]
    H["Health Assessment<br/>BHI 0-100 · 5 dimensions"]
    K["Risk Classification<br/>4 tiers + override"]
    RF["Retrofit Decision<br/>RP-v1.0 priority · REC-v1.0 rules"]
    EV["Evidence Chain<br/>recommendation → anomaly → sensor → record"]
    EXP["AI Explanation<br/>natural language, reads only"]

    B --> S --> R --> A --> H --> K --> RF
    RF --> EV
    RF --> EXP
    H --> EXP
    K --> EXP

    A -.->|"severity + method + explanation"| EV
```

Each layer carries a version identifier (`ANOM-v1.0`, `BHI-v1.0`, `RISK-v1.0`,
`RP-v1.0`, `REC-v1.0`, `AI-v1.0`) so a stored or displayed result can be
interpreted against the parameters that produced it.

---

## 3. AI and retrieval

```mermaid
flowchart LR
    subgraph ENG["Engineering side"]
        CTX["Engineering Context<br/>building · sensors · monitoring<br/>health · risk · retrofit"]
        EE["Engineering Evidence<br/><i>about this building</i>"]
    end

    subgraph KNO["Knowledge side"]
        KBDOC["Knowledge Base<br/>5 internal documents"]
        CH["Chunker<br/>section-based · 23 chunks"]
        RET["Retriever<br/>TF-IDF + cosine · top-3"]
        KE["Knowledge Evidence<br/><i>general background</i>"]
    end

    PROMPT["Prompt assembly"]
    PROV["AI Provider<br/>Mock (default) / OpenAI-compatible"]
    GUARD["Runtime safety guard<br/>43 redlines · schema validation"]
    OUT["AI Response<br/>answer · key findings<br/>evidence · knowledge_evidence<br/>actions · disclaimer"]

    CTX --> EE --> PROMPT
    KBDOC --> CH --> RET --> KE --> PROMPT
    PROMPT --> PROV --> GUARD --> OUT
```

### Engineering Evidence ≠ Knowledge Evidence

The two are kept apart at every layer:

| | Engineering Evidence | Knowledge Evidence |
|---|---|---|
| **Meaning** | Measurements and derived results **about this building** | General engineering concepts, **not about this building** |
| **Source** | Sensors, monitoring records, anomalies, BHI, risk, retrofit | The internal knowledge base |
| **Priority** | Absolute — it is the basis of the response | Background explanation only |
| **Schema** | `AIResponse.evidence` | `AIResponse.knowledge_evidence` |
| **Prompt key** | `engineering_data_context` | `knowledge_evidence` |
| **UI** | Evidence section | Knowledge Sources section (distinct colour) |
| **Can it prove a condition in this building?** | Yes | **No** |

The system prompt states that engineering data has absolute priority, and the
knowledge context is declared untrusted. The retrieved knowledge evidence is
forced from the retriever — anything the model returns for that field is
discarded.

---

## 4. Request lifecycle (read path)

```mermaid
sequenceDiagram
    participant U as Browser
    participant A as FastAPI
    participant S as Service layer
    participant E as Analytics engine
    participant D as SQLite

    U->>A: GET /api/buildings/{id}/risk
    A->>S: classify building
    S->>D: load latest assessment
    S->>D: load sensors + monitoring series (batched)
    S->>E: run_anomaly_detection(sensors, series_map)
    E-->>S: anomalies
    S->>E: compute_health_assessment(anomalies, series_map)
    E-->>S: BHI result
    S->>E: classify_risk(bhi, anomalies)
    E-->>S: risk tier + version
    S-->>A: response payload
    A-->>U: 200 JSON
```

For paths that need several of these results (the AI context build, the
aggregate endpoints), a request-scoped analysis object is computed **once per
building** and passed down the call stack, so no layer recomputes what an
earlier layer already produced.

---

## 5. Data model

```mermaid
erDiagram
    BUILDINGS ||--o{ COMPONENTS : contains
    BUILDINGS ||--o{ SENSORS : has
    COMPONENTS ||--o{ SENSORS : mounts
    SENSORS ||--o{ MONITORING_RECORDS : produces
    BUILDINGS ||--o{ HEALTH_ASSESSMENTS : assessed_by
    BUILDINGS ||--o{ RISK_ALERTS : raises
    BUILDINGS ||--o{ ENGINEERING_NOTES : annotated_by
    BUILDINGS ||--o{ RETROFIT_RECOMMENDATIONS : "table exists (unused)"

    BUILDINGS {
        int id PK
        string name
        string building_type
        string structure_type
        int floors
        int design_life
        int current_age
    }
    SENSORS {
        int id PK
        int building_id FK
        string sensor_type
        string unit
        string status
    }
    MONITORING_RECORDS {
        int id PK
        int sensor_id FK
        datetime timestamp
        float value
        string quality_flag
    }
    HEALTH_ASSESSMENTS {
        int id PK
        int building_id FK
        float score
        string calculation_version
    }
    RISK_ALERTS {
        int id PK
        int building_id FK
        int sensor_id FK
        string detection_method
        string severity
    }
```

Eight tables in total. `retrofit_recommendations` exists in the schema but is
not currently written to — recommendations are computed in real time.

---

## 6. Deployment shape (current)

```mermaid
flowchart LR
    BROWSER["Browser"]
    VITE["Vite dev server<br/>:5173"]
    UVICORN["uvicorn<br/>:8000"]
    SQLITE[("buildhealth.db")]

    BROWSER --> VITE
    VITE -->|"/api proxy"| UVICORN
    UVICORN --> SQLITE
```

Single machine, local development only. No cloud deployment, no authentication,
no rate limiting. CORS is restricted to local development origins.
