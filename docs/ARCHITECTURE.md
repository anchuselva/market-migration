# High-Level Architecture & Hybrid Cloud Migration Strategy
## 24/7 Financial Exchange: Zero-Downtime, Zero-Data-Loss Hybrid Cloud Migration

---

## 1. Executive Summary & Challenge Context

Tier-1 financial exchanges cannot tolerate maintenance windows, data discrepancies, or unplanned downtime. In **Challenge 1.2**, we architect and implement a **Zero-Downtime, Zero-Data-Loss Hybrid Cloud Migration Strategy** that decouples legacy monolithic on-premise matching systems and smoothly migrates state to a modern cloud-native architecture on AWS (Amazon Aurora Multi-AZ PostgreSQL & Apache Kafka / AWS MSK).

### Core Architectural Pillars
1. **Clean Architecture (Hexagonal / Ports & Adapters)**: Pure enterprise business rules separated from external storage and streaming drivers.
2. **Decoupled Shadow Running**: Live trades fan out concurrently into both on-premise transactional databases and cloud shadow datastores via asynchronous message brokers.
3. **Out-of-Band Continuous Parity Auditor**: Asynchronous, zero-impact ledger reconciliation auditing count, volume, and cryptographic identity drift without impacting ultra-low-latency order matching.
4. **Instant Zero-Loss Rollback / Failback**: If cloud infrastructure degrades or fails, the on-premise matching engine remains authoritative, guaranteeing 0.00% data loss and zero disruption to market participants.

---

## 2. High-Level Architecture Diagram (Clean Architecture)

```mermaid
graph TD
    subgraph "External Feeds & Market Participants"
        MarketFeed["Synthetic Market Trade Feed<br/>(1,000+ Executions/sec)"]
    end

    subgraph "Data Hygiene Layer"
        Sanitizer["Data Cleanser (cleanse.py)<br/>• Validates IDs & Symbols<br/>• Enforces price/qty > 0<br/>• Normalizes ISO 8601 UTC"]
    end

    subgraph "Application Core (Ports & Adapters)"
        subgraph "Domain Layer (Pure Enterprise Rules)"
            TradeEntity["Trade Entity<br/>• Invariant Validation<br/>• dollar_volume()"]
            OrderEntity["Order Entity"]
            InstrumentEntity["Instrument Entity"]
        end

        subgraph "Ports Layer (Abstract Interfaces)"
            RepoPort["TradeRepositoryPort<br/>• save()<br/>• count()<br/>• total_volume()<br/>• get_all_ids()"]
            EventBusPort["EventBusPort<br/>• publish()<br/>• subscribe()"]
        end

        subgraph "Services Layer (Use Case Orchestration)"
            DualIngestion["DualIngestionService<br/>• Decoupled Shadow Running<br/>• Chaos Hook Injection"]
            ParityService["ParityService<br/>• Out-of-Band Auditor<br/>• Idempotent Reconciliation"]
        end
    end

    subgraph "Infrastructure Adapters"
        Broker["MemoryEventBus / Kafka Broker<br/>(Asynchronous Queue Fan-out)"]
        LegacyAdapter["SqliteTradeAdapter / PostgresLegacy<br/>(Port 5432 - Idempotent UPSERT)"]
        CloudAdapter["PostgresCloudAdapter / Aurora<br/>(Port 5433 - ON CONFLICT DO NOTHING)"]
    end

    subgraph "Physical Datastores"
        LegacyDB[("Legacy Store<br/>Primary On-Prem Hot Master")]
        CloudDB[("Cloud Target Store<br/>Shadow Store -> Aurora Master")]
    end

    MarketFeed --> Sanitizer
    Sanitizer --> DualIngestion
    DualIngestion --> Broker
    Broker -->|Consumer A| LegacyAdapter
    Broker -->|Consumer B (Shadow)| CloudAdapter
    LegacyAdapter --> LegacyDB
    CloudAdapter --> CloudDB

    ParityService -.->|Poll Out-of-Band| LegacyDB
    ParityService -.->|Poll Out-of-Band| CloudDB
```

---

## 3. The 5-Phase Migration Pattern

### Phase 1: Decoupled Dual-Ingestion (Shadow Mode)
- Every trade executed by the matching engine is published to an asynchronous event bus topic (`market.trades`).
- Independent consumer workers persist transactions to:
  - **Primary On-Prem Store** (Legacy SQLite / PostgreSQL).
  - **Cloud Shadow Store** (AWS Aurora PostgreSQL).
- Cloud storage latency or network jitter never bubbles back to block the primary matching engine or trade confirmation to brokers.

### Phase 2: Out-of-Band Continuous Parity Auditing
- Parity auditing runs in a separate thread/process to prevent locking production tables.
- Evaluates:
  $$\Delta_{\text{count}} = |N_{\text{legacy}} - N_{\text{cloud}}|$$
  $$\Delta_{\text{volume}} = |V_{\text{legacy}} - V_{\text{cloud}}|$$
- Status flags:
  - `IN_PARITY`: $\Delta_{\text{count}} = 0 \land \Delta_{\text{volume}} = 0$
  - `DRIFT_DETECTED`: $\Delta_{\text{count}} > 0 \lor \Delta_{\text{volume}} > 0$

### Phase 3: Chaos Injection & Anomaly Detection
- System actively injects simulated network degradation or Availability Zone (AZ) failure into the cloud shadow consumer.
- The out-of-band auditor detects drift in near real-time without interrupting on-premise order execution.

### Phase 4: Idempotent Catch-Up Reconciliation
- The reconciliation engine identifies missing `trade_id` records ($S_{\text{missing}} = S_{\text{legacy}} \setminus S_{\text{cloud}}$).
- Backlog replay streams missing records into the cloud database using idempotent `INSERT OR IGNORE` / `ON CONFLICT (trade_id) DO NOTHING` semantics.
- Audit ledger returns to `IN_PARITY` with 100% data consistency.

### Phase 5: Zero-Downtime Cutover & Hot-Standby Rollback
- **Cutover**: When shadow parity maintains 100% consistency across consecutive settlement cycles, DNS and API gateway routes traffic to Cloud Aurora as the Primary Master.
- **Rollback Guarantee**: The on-premise database remains populated and warm as a Hot Standby. If any anomaly occurs post-cutover, instant rollback reverts traffic with **0.00% data loss**.

---

## 4. Architectural Boundaries & Directory Layout

```
market-migration/
├── src/
│   ├── domain/                  # Enterprise business rules (Zero framework dependencies)
│   │   ├── models.py            # Trade, Order, Instrument dataclasses
│   │   └── exceptions.py        # Domain-specific validation invariants
│   ├── ports/                   # Abstract contracts (Hexagonal Ports)
│   │   ├── repository_port.py   # Trade persistence port
│   │   └── event_bus_port.py    # Publish-subscribe broker port
│   ├── adapters/                # Infrastructure drivers (Hexagonal Adapters)
│   │   ├── sqlite_adapter.py    # Idempotent SQLite persistence
│   │   ├── postgres_adapter.py  # Production Aurora/Postgres adapter
│   │   └── memory_bus.py        # Asynchronous decoupled message broker
│   ├── services/                # Application orchestration & use cases
│   │   ├── ingestion_service.py # Dual-stream shadow dispatcher with chaos hook
│   │   └── parity_service.py    # Out-of-band reconciliation & drift monitor
│   └── api/                     # REST/OpenAPI contracts
│       ├── routes.py            # Migration orchestration endpoints
│       └── openapi_spec.yaml    # OpenAPI 3.0 specification
├── data/
│   ├── raw_trades.csv           # Raw feed with intentional anomalies
│   ├── cleanse.py               # Data sanitation pipeline
│   └── cleaned_trades.csv       # Validated trade records
├── docker/
│   ├── docker-compose.yml       # Legacy DB (5432) & Cloud DB (5433)
│   └── init-db.sql              # Relational DDL with check constraints
├── tests/
│   ├── test_domain.py           # Domain model invariants & validation
│   └── test_parity.py           # Ingestion parity, drift, and recovery tests
├── .github/
│   └── workflows/
│       └── devsecops.yml        # CI/CD: flake8, pytest, Trivy container security
├── docs/
│   ├── ARCHITECTURE.md          # This High-Level Design document
│   └── MENTOR_PRESENTATION.md   # Script and presentation defense
├── requirements.txt
└── main.py                      # Multi-threaded runner: Dual Stream + Auditor + Rollback drill
```

---

## 5. Security & DevSecOps Strategy

- **Static Analysis**: `flake8` enforces strict PEP 8 formatting, import hygiene, and complexity limits.
- **Automated Testing**: `pytest` executes 100% of unit, domain invariant, idempotency, and parity audit test cases.
- **Vulnerability Scanning**: `aquasecurity/trivy-action` scans file systems and container images for known CVEs before deployment.
- **Idempotency**: All database queries enforce strict primary key uniqueness and `ON CONFLICT DO NOTHING` guarantees to eliminate race conditions.
