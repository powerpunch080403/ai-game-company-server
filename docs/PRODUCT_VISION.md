# Product Vision and Long-Term Direction

This document outlines the product definition, core principles, architectural topology, and evolutionary stages of the AI Project Control Server. 

---

## 1. Product Definition

The AI Project Control Server is **a project control plane for coordinating human contributors and AI workers**. 

It is designed to orchestrate software development workflows by acting as a management and tracking layer. It is **not** primarily:
* An AI model or LLM.
* A standalone coding agent (e.g., it does not contain the inner loop of code generation directly).
* A replacement for Git.
* A game runtime server.
* A generic chat application.

Instead, the control server focuses on coordinating work around a project by centralizing:
* **Task ownership** (who is working on what).
* **Work scopes and locks** (preventing overlapping modifications).
* **Leases and heartbeats** (tracking active worker node assignments).
* **Dependencies** (coordinating task order).
* **Worker capabilities** (matching tasks to appropriate workers).
* **Reports and approvals** (reviewing and accepting completed work).
* **Artifact management** (tracking output files and logs).
* **Project context and memory** (providing relevant decisions and rules).
* **Git integration** (automating branch creation, tracking base commits, and managing the merge queue).

```text
+-------------------------------------------------------------+
|               AI Project Control Server                     |
|  (Task State, Leases, Scopes/Locks, Context Memory, Queue)  |
+------------------------------+------------------------------+
                               |
            +------------------+------------------+
            |                                     |
            v                                     v
+-----------------------+             +-----------------------+
|      Git Server       |             |   Worker Runtimes    |
| (Source of Truth for  |             | (Local/Remote Agents  |
|  code & merges)       |             |  running tools)       |
+-----------------------+             +-----------------------+
```

> [!NOTE]
> The server acts as a control plane above Git and worker runtimes. Git remains the source of truth for code history and merging. The control server manages who should work on what, under which constraints, and how results are reviewed.

---

## 2. Human and AI Team Model

The intended long-term topology of the collaboration environment divides responsibilities between a central authority and distributed, capable workers.

```text
Central Authority / Control Server
├─ project state
├─ tasks
├─ leases
├─ scopes and locks
├─ reports
├─ approvals
├─ artifacts
├─ shared project memory
└─ audit/history

Human or AI Worker Nodes
├─ coding tools
├─ image tools
├─ voice/audio tools
├─ test/build tools
└─ local or remote models
```

### Key Topology Rules:
* **Single Authoritative Control Server**: Each project is managed by exactly one authority server, which acts as the shared source of truth for tasks, active leases, locks, and project history.
* **Worker Nodes**: Human team members and AI workers operate one or more worker nodes. These nodes do not independently decide global project state; they request task leases, check out branches, execute local tools (coding, assets, testing, or building), and submit worker reports.
* **Git Integration**: Git is the absolute source of truth for code history, commits, branches, diffs, pull requests, and merges. The control server coordinates activities around these Git repositories.

---

## 3. Task Ownership Invariant

To keep branch management, lock safety, and merge tracking unambiguous, the system enforces a strict architectural rule:

> [!IMPORTANT]
> **Task Ownership Invariant**: One task may have at most one active worker lease at any given time.

A task represents an atomic unit of responsibility. To support features requiring multiple modalities (such as coding, art, voice acting, and testing), tasks should be split and coordinated under a larger container.
* Multiple modalities should normally be split into related tasks.
* Related tasks are grouped under an **Epic**, **SubEpic**, or a future **task group / work package** layer.
* Each task has its own responsible worker type, primary branch, and context thread.

### Example: Enemy Character Prototype Feature
```text
Feature Epic: Enemy Character Prototype
  ├─ Task A: Generate concept art (assigned to image_worker)
  ├─ Task B: Produce voice lines (assigned to voice_worker)
  ├─ Task C: Implement enemy behavior (assigned to code_worker)
  └─ Task D: Integrate assets and code (assigned to integration_worker or human)
```

---

## 4. Capability-Based Workers

In the long-term design, workers should not be permanently restricted to a single hardcoded role (e.g., only a `code_worker` or an `image_worker`). Instead, the system plans to adopt a capability-based routing model.

### Modality & Capability Model:
* **Worker Advertisement**: A worker node may advertise multiple capabilities to the server:
  * `code`, `git`, `test`, `review`
  * `image_generation`, `image_editing`, `vision`
  * `voice_generation`, `audio_editing`
  * `documentation`
* **Task Requirements**: Tasks declare their constraints:
  * `task_kind`
  * `required_capabilities`
  * `preferred_capabilities`
* **Worker Profiles**: Workers report their available resources:
  * `capabilities` and `available_tools`
  * `current_load` and `max_concurrency`
  * `provider` or `model` configuration
  * `resource limits` and `quota information`

> [!NOTE]
> Under this model, a multimodal worker node can execute image generation tasks when they are queued, and automatically accept compatible coding, testing, or documentation tasks when the image queue is empty.
> 
> *Status: Capability-based worker routing is a future direction and is not yet implemented.*

---

## 5. Team Operating Protocol

A successful development process relies on clear operating rules. The control server is designed to act as the enforcer of these rules, defining the "grammar" of the shared workflow.

* **Operating Rules**: Teams define how features are utilized:
  * Branch and worktree strategies.
  * Write scope ownership and lock requirements.
  * Task creation rules and review policies.
  * Test requirements, approval policies, and merge policies.
  * Violation handling (e.g., how to respond to scope violations) and worker Standard Operating Procedures (SOPs).
* **Project Workflow Policy**: In the future, the control server will store and programmatically enforce these team-defined policies.
  
> [!NOTE]
> Leases, scopes, locks, reports, and approvals are the grammar of a shared operating language used by humans and AI workers.
> 
> *Status: The workflow policy engine is a conceptual future feature and does not currently exist.*

---

## 6. Memory and Coordination Agent

Project memory is split into two distinct tiers to preserve reliability and context:

1. **Authoritative Current State**: Database records (SQLite/PostgreSQL) representing tasks, leases, locks, reports, branches, approvals, and configuration. **The database is the absolute source of truth.**
2. **Contextual Memory**: Searchable indices of past decisions, thread summaries, design reasoning, preferences, lessons learned, and related works. **Memory provides context and recommendations.**

### Conceptual Coordination Flow:
```text
Human/AI expresses intent to work
  --> Search similar historical tasks
  --> Inspect active leases and locks
  --> Retrieve related decisions and architectural context
  --> Check for potential duplication or conflicts
  --> Recommend: Join existing task, split task, delay, or create task
```

*Example recommendation response:*
> "A related task ('Enemy Pathfinding Optimization') is already active under another team member on branch `feat/enemy-nav`. Consider joining the existing task or creating a dependent integration task."

> [!NOTE]
> *Status: The coordination agent and vector-based memory search are future goals and are not currently implemented.*

---

## 7. Personal, Team, and Enterprise Direction

To ensure sustainable growth, the control server will evolve through three deployment models, all sharing the same core codebase and architecture rather than diverging into separate repositories.

### Personal / Standalone
* **Target**: Single human developer.
* **Architecture**: Local control server, SQLite database, local or remote AI workers, simple setup with no complex team identity system.
* **Focus**: Fast setup, ease of use, local workspace coordination.

### Team
* **Target**: Small groups of 2 to 50 members.
* **Architecture**: Centrally hosted authority server, multiple remote worker nodes, user/node identity validation, shared relational database (PostgreSQL or equivalent), fine-grained permissions, audit history, and reliable backup/recovery.
* **Focus**: Task conflict detection, permission enforcement, and team coordination.

### Enterprise
* **Target**: Organizations with 50+ users.
* **Architecture**: High-availability deployments, Single Sign-On (SSO) integration, advanced Role-Based Access Control (RBAC), multi-tenant isolation, managed backup/disaster recovery, detailed audit logs, and compliance enforcement.
* **Focus**: Scale, compliance, administrative controls, and policy templates.

---

## 8. Frontend Direction

The control server aims to transition away from its initial dependency on Discord as its primary interface.

* **Current State**: Discord serves as an effective, low-overhead interface for chat, notifications, and light task control.
* **Future Standalone Interface**: A browser-based web application with optional desktop packaging.
* **Planned Web App Features**:
  * Project browser and dashboard.
  * Epic, SubEpic, and Task hierarchy views.
  * Task detail, discussion threads, and change packages.
  * Worker node status, loads, and capability monitors.
  * Visual scope and lock trackers.
  * Test results and report inspections.
  * Interactive merge candidate review.
  * Artifact previews and system configuration logs.

> [!NOTE]
> The preferred technical stack is a **FastAPI backend** paired with a **browser-based frontend** (to be packaged as a desktop app later if needed). No specific frontend framework (React, Vue, Svelte, etc.) is locked in at this stage.

---

## 9. Database Evolution

To accommodate growing scale without introducing unnecessary complexity too early, the storage layer will evolve gradually:

* **Current**: SQLite for personal, local development.
* **Possible Intermediate**: libSQL or Turso-style SQLite-compatible remote or replicated deployment for lightweight team settings.
* **Future Team/Enterprise**: PostgreSQL or another robust relational database for high-concurrency and production team use.

> [!NOTE]
> The architectural priority is to maintain clean isolation in the storage layer (`app/repository.py` or equivalent data access layers) so that changing database backends is straightforward when requirements demand it. No active migration is currently scheduled.

---

## 10. Python Direction

Python and FastAPI remain the appropriate technology stack for the project control plane. Python provides rapid iteration, excellent ecosystem integration with AI tools/frameworks, and clear web API routing.

Runtime speed bottlenecks are expected to occur in other areas before Python's execution speed becomes a limiting factor:
* Database concurrency and connection pooling.
* Task queue design and scheduling latency.
* Worker-node network coordination.
* Workspace sandboxing and file system isolation.
* Fine-grained permissions and authentication.
* Deployment reliability and recovery procedures.

Specialized components (e.g., performance-critical file diffing, binary package scanners, or low-latency queue dispatchers) may be written in other languages in the future only when measured performance profiling justifies it. There is **no immediate plan or proposal for a codebase rewrite**.

---

## 11. Sustainable Development Plan

The project development model prioritizes sustainable, incremental growth based on real-world usage rather than speculative deadlines or aggressive schedules.

```text
Use server in real personal projects
  --> Use it with friends on small team projects
  --> Add features when real usage exposes a need
  --> Avoid speculative enterprise complexity too early
  --> Preserve backward compatibility and maintain clear tests/docs
```

The roadmap progresses through developmental phases rather than fixed dates:

### Phase 0 — Current V1 Acceptance
* **Goal**: Complete the manual Owner smoke test as defined in [`docs/V1_SMOKE_TEST.md`](file:///c:/Users/user2/.gemini/antigravity/scratch/ai-game-company-server/docs/V1_SMOKE_TEST.md).
* **Requirements**: Record the smoke test outcome honestly. No official V1.5 work begins until the V1 smoke test PASS result is recorded.
* *Current status: V1 acceptance result is pending.*

### Phase 1 — Personal Standalone Product
* **Goals**:
  * Deliver a stable local development workflow.
  * Create a standalone frontend alpha.
  * Simplify setup, configuration, and backup/recovery procedures.
  * Conduct real-world solo project dogfooding.
  * Make Discord integration optional rather than required.

### Phase 2 — Small-Team Alpha (Future Direction)
* **Goals**:
  * Establish a centralized authority server configuration.
  * Support remote worker-node registration and identity.
  * Introduce basic user management, teams, and permission sets.
  * Coordinate tasks, leases, and locks across multiple nodes.
  * Perform small-team testing with friends.

### Phase 3 — Small-Team Product (Future Direction)
* **Goals**:
  * Polish the standalone web frontend.
  * Simplify installation, migration, and update packages.
  * Switch to PostgreSQL or similar shared storage.
  * Implement robust node recovery, task timeouts, and audit logs.
  * Integrate workflow policy templates and capability-based worker scheduling.

### Phase 4 — Larger Organizations (Future Direction)
* **Goals**:
  * Support multi-project organization management.
  * Implement advanced SSO, RBAC, and policy compliance enforcement.
  * Introduce operational monitoring and high-availability deployment structures.

---

## 12. Product Validation

The commercial and functional value of the Project Control Server must be validated through usage data rather than theoretical assumptions.

### Key Validation Questions:
1. Does the server reduce duplicate work among team members?
2. Does it decrease code merge and scope conflicts?
3. Does it clarify task responsibility and context for developers/agents?
4. Does it reduce owner review effort and cognitive load?
5. Does it improve visibility across human and AI contributions?
6. Is the setup and coordination overhead lower than the productivity benefits gained?
7. Will a small team continue to use the server after completing their first project?

### Initial Target User Groups:
* Solo developers building complex personal projects.
* Small groups of friends working on game jams or side projects.
* Indie game studios or small software teams.
* Student project groups at universities.
* Small team projects utilizing multiple autonomous AI agents.

---

## 13. Commercial Direction

While commercial options may be explored in the future, the repository remains focused on building a useful, open control plane.

* **Product Tiers**: Future pricing tiers may include *Personal* (free/self-hosted), *Team* (hosted or self-hosted team features), and *Enterprise* (advanced administration).
* **Decisions**: No pricing decisions or licensing changes are required or planned at this time.
* **Priority**: Product-market fit is unproven. Real dogfooding and small-team testing must precede any monetization effort.
