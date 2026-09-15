# MASTER ENGINEERING MANDATE
# Enterprise Decision, Data, Process, Security & Agent Platform

You are acting as a Principal Software Engineer, Software Architect,
AI/Agent Systems Engineer, Data Engineer, Cloud Architect,
DevSecOps Engineer, QA Engineer, and technical documentation author.

Your task is to DESIGN, IMPLEMENT, TEST, DOCUMENT, HARDEN,
and package a serious production-oriented enterprise software platform.

This must NOT be a toy AI demo.
This must NOT be a shallow dashboard with mocked features.
This must NOT be an "AI-looking" website whose main value is visual effects.

The repository must look and behave like software created by an engineer
who understands software architecture, backend engineering, databases,
security, data engineering, distributed systems, testing, cloud architecture,
agent orchestration, maintainability, and operational concerns.

The project is also intended to serve as:

1. A professional software-engineering portfolio project.
2. A Fachinformatiker Daten- und Prozessanalyse / IHK-related project base.
3. A Praktikum application showcase.
4. A real platform that can continue evolving after the initial implementation.
5. A learning codebase whose owner can read, explain, modify, debug,
   and extend every important subsystem.

Do not optimize for producing the largest amount of code quickly.

Optimize for:
correctness,
architecture,
clarity,
security,
testability,
maintainability,
observability,
explainability,
portability,
and real end-to-end functionality.

--------------------------------------------------
0. AUTONOMY AND ENGINEERING BEHAVIOR
--------------------------------------------------

Do not blindly follow this specification when a technically superior
solution exists.

You are explicitly authorized to improve architectural decisions when
you can justify them.

However:

- document every major architectural decision;
- explain important tradeoffs;
- do not silently replace requirements;
- do not introduce unnecessary complexity merely to appear sophisticated;
- do not introduce microservices where modular boundaries are enough;
- do not introduce distributed infrastructure without an actual reason;
- do not create fake implementations to make the UI appear complete.

Before writing substantial code:

1. inspect the complete repository;
2. understand existing code and conventions;
3. create or update the architecture plan;
4. identify dependencies between modules;
5. identify security boundaries;
6. identify test requirements;
7. identify data flows;
8. identify assumptions;
9. define acceptance criteria.

Maintain:

docs/IMPLEMENTATION_PLAN.md
docs/ARCHITECTURE.md
docs/ROADMAP.md
docs/STATUS.md
docs/adr/
docs/security/
docs/modules/
docs/testing/
docs/ihk/
docs/learning/

Do not stop after scaffolding.

Continue implementing vertical slices until useful end-to-end workflows
actually work.

After each substantial implementation phase:

- run formatting;
- run static analysis;
- run type checking;
- run unit tests;
- run integration tests;
- run relevant end-to-end tests;
- run security checks;
- fix failures;
- update documentation;
- update STATUS.md.

Never claim a feature is complete if the main workflow is mocked,
disabled, untested, or dependent on nonexistent infrastructure.

Clearly distinguish:

IMPLEMENTED
PARTIALLY IMPLEMENTED
EXPERIMENTAL
NOT IMPLEMENTED
REQUIRES EXTERNAL CREDENTIALS
NOT LIVE-TESTED

Do not create fake successful test results.

--------------------------------------------------
1. PRODUCT VISION
--------------------------------------------------

Build an enterprise operations and decision-support platform capable of
understanding an organization's:

- business objectives;
- IT environment;
- infrastructure;
- datasets;
- cloud environment;
- applications;
- security posture;
- workflows;
- production/business processes;
- costs;
- availability requirements;
- backup requirements;
- compliance constraints;
- users and permissions;
- customer-support knowledge;
- AI-agent requirements.

The platform combines traditional deterministic software with AI agents.

IMPORTANT PRINCIPLE:

LLMs must not replace deterministic engineering logic when deterministic
logic is more reliable.

For important decisions, combine:

rules,
calculations,
validated input,
structured data,
decision matrices,
domain algorithms,
historical evidence,
and AI reasoning.

The AI should explain and augment engineering decisions, not invent them.

--------------------------------------------------
2. ARCHITECTURAL PHILOSOPHY
--------------------------------------------------

Prefer initially:

a well-structured modular architecture with explicit domain boundaries

over:

a large collection of artificial microservices.

However, design module interfaces so major domains could later be
extracted into independent services if scaling requires it.

Use principles from:

- clean architecture;
- hexagonal architecture / ports and adapters where useful;
- domain-driven modularity;
- dependency inversion;
- explicit interfaces;
- typed contracts;
- separation of business logic and infrastructure;
- secure-by-default engineering.

Do not overuse patterns where simple code is clearer.

--------------------------------------------------
3. RECOMMENDED TECHNOLOGY BASELINE
--------------------------------------------------

Evaluate current stable versions before implementation.

Preferred baseline unless a better choice is justified:

Backend:
- Python
- FastAPI
- Pydantic
- SQLAlchemy
- Alembic
- PostgreSQL
- pgvector when vector retrieval is justified
- Redis for caching / jobs where appropriate
- background worker architecture
- OpenAPI

AI:
- OpenAI Responses API
- OpenAI Agents SDK
- structured outputs
- tool/function calling
- explicit guardrails
- human approval boundaries
- tracing
- evaluation framework

Do not hard-code a single model identifier throughout the codebase.

Create model configuration and routing.

Support a deterministic/mock LLM provider for tests.

Frontend:
- TypeScript
- React / Next.js or a justified equivalent
- strongly typed API integration
- accessible components
- responsive desktop-first enterprise interface

Visualization:
choose appropriate professional libraries for:
- statistical charts;
- process diagrams;
- infrastructure diagrams;
- dependency graphs;
- agent execution graphs.

Data:
- Pandas / Polars depending workload
- DuckDB where useful for analytical workloads
- optional adapters for larger distributed processing later

Object storage:
- S3-compatible abstraction
- local MinIO for development if appropriate

Observability:
- structured logging;
- trace IDs;
- metrics;
- OpenTelemetry where justified;
- health/readiness endpoints.

Do not introduce Kafka, Kubernetes, service mesh, Spark, etc.
solely for résumé decoration.
Introduce them only behind justified architectural boundaries.

--------------------------------------------------
4. CORE DOMAIN MODULES
--------------------------------------------------

Implement the system using strongly separated domain modules.

Each module should expose APIs/services that can operate independently
but integrate through the platform.

==================================================
MODULE A — COMPANY & IT INTAKE
==================================================

Create a comprehensive organizational intake system.

Capture:

company size,
industry,
locations,
employees,
IT staff,
applications,
current infrastructure,
network structure,
workloads,
databases,
storage,
data volume,
traffic,
growth expectations,
latency requirements,
availability requirements,
RTO,
RPO,
security sensitivity,
regulatory considerations,
budget,
CAPEX/OPEX preference,
current vendors,
cloud experience,
internal skills,
legacy systems,
remote-work needs,
business priorities,
cost-vs-performance preference.

Build reusable typed domain models.

The user must be able to save multiple company scenarios and compare them.

==================================================
MODULE B — IT ARCHITECTURE ADVISOR
==================================================

Implement an engineering decision-support system for determining whether
a company should use combinations of:

SaaS,
PaaS,
IaaS,
on-premises,
private cloud,
public cloud,
hybrid infrastructure.

Do NOT ask an LLM alone to decide.

Create an explainable weighted decision engine.

Evaluate dimensions such as:

cost,
performance,
availability,
operational complexity,
staff requirements,
security,
vendor lock-in,
scalability,
data sensitivity,
latency,
maintenance,
backup,
disaster recovery,
time-to-market.

Return:

recommended architecture,
alternative architectures,
decision score,
confidence,
assumptions,
risks,
cost implications,
advantages,
disadvantages,
why alternatives lost,
required hardware where relevant,
network considerations,
migration considerations.

Provide economic-mode and performance-mode optimization,
plus configurable weighting.

Implement TCO/CAPEX/OPEX estimation architecture.

Cost catalog data must be versioned/configurable rather than invented.

==================================================
MODULE C — DATA INTELLIGENCE
==================================================

Provide a serious Data Analysis / Data Engineering environment.

Accept where appropriate:

CSV
JSON
XLSX
Parquet
database sources.

Implement:

schema discovery,
type inference,
missing-data analysis,
duplicate detection,
outlier detection,
invalid-value detection,
distribution profiling,
data-quality scoring,
statistical summaries,
correlation analysis,
categorical analysis,
time-series inspection where applicable.

Data cleaning must have TWO modes:

MANUAL MODE
AI-ASSISTED MODE

Manual mode must expose understandable transformation operations.

AI-assisted mode may suggest transformations but must produce a
reproducible transformation plan.

Never silently mutate original datasets.

Preserve:

raw dataset,
transformation pipeline,
cleaned version,
metadata,
lineage,
who initiated changes,
timestamps.

Allow preview-before-commit.

Generate professional interactive visualizations.

Create exportable analytical reports.

Support reusable data-quality rules.

Where useful provide:

anomaly detection,
clustering,
forecasting hooks,
feature analysis.

Do not automatically apply ML where normal statistics are sufficient.

==================================================
MODULE D — PROCESS INTELLIGENCE & OPTIMIZATION
==================================================

Create a process-analysis environment connected to Data Intelligence.

Support event-log/process data.

Calculate where possible:

cycle time,
waiting time,
throughput,
bottlenecks,
resource utilization,
rework,
failure points,
queue behavior,
process variance.

Investigate using a suitable process-mining library if justified.

Allow:

manual process analysis,
AI-assisted analysis.

Generate process diagrams and proposed optimized workflows.

Recommendations must connect to evidence and measured KPIs.

Show:

current process,
identified bottleneck,
recommended change,
expected benefit,
risk,
cost,
measurement required to confirm improvement.

Allow results from Data Intelligence to be passed explicitly into
Process Intelligence through typed contracts rather than raw prompt text.

==================================================
MODULE E — CLOUD ARCHITECTURE, FINOPS & RESILIENCE
==================================================

Create a cloud architecture module that reasons about:

public cloud,
private cloud,
hybrid cloud,
SaaS,
PaaS,
IaaS.

Support cloud-provider adapters in a way that can later accommodate:

Azure,
AWS,
and potentially other providers.

Initial cloud connections should default to READ ONLY.

Provide:

resource inventory,
architecture review,
cost analysis,
FinOps recommendations,
tagging strategy,
rightsizing suggestions,
backup strategy,
disaster recovery planning,
RTO/RPO modeling,
availability-zone/region considerations,
storage policy,
lifecycle recommendations,
network architecture suggestions,
IAM/RBAC planning,
least-privilege recommendations.

Provide Terraform/IaC recommendations where appropriate,
but never apply infrastructure changes automatically without an
explicit approval workflow.

Separate:

PLAN
REVIEW
APPROVE
APPLY

as different states.

==================================================
MODULE F — SECURITY ASSESSMENT LAB
==================================================

Build a professional defensive security-assessment subsystem.

THIS MODULE MUST BE REALISTIC BUT SAFE.

It must operate only against:

- repositories owned by the operator;
- explicitly authorized targets;
- isolated development environments;
- deliberately vulnerable security-lab containers.

Create an explicit scope manifest.

Never scan arbitrary Internet targets.

Implement non-destructive capabilities such as:

source-code security analysis,
SAST,
dependency vulnerability scanning,
secret detection,
container/image vulnerability scanning,
SBOM generation,
configuration analysis,
HTTP security-header checks,
TLS/configuration review,
authorized baseline DAST,
OWASP-oriented checks.

Potential tools may include appropriately configured:

Semgrep,
Bandit,
pip-audit,
npm audit,
Trivy,
OWASP ZAP baseline/passive scanning,

or superior maintained alternatives.

Every tool must run through a controlled adapter.

Never blindly execute model-generated shell commands.

Do not implement:

credential theft,
persistence,
malware,
stealth/evasion,
destructive exploitation,
data exfiltration,
automatic exploitation of third-party systems.

Build a deliberately vulnerable LOCAL security lab using isolated
containers if useful.

Bind vulnerable labs safely and prevent unintended Internet exposure.

Generate findings containing:

finding ID,
asset,
severity,
CVSS where applicable,
CWE,
OWASP mapping,
evidence,
confidence,
false-positive status,
recommended remediation,
verification instructions,
status,
owner.

Allow human analysts to confirm/reject findings.

The AI Security Agent analyzes results and prioritizes remediation.

The scanner produces evidence.
The LLM interprets evidence.
The LLM must never fabricate scanner output.

==================================================
MODULE G — AGENT PLATFORM
==================================================

Build the AI architecture as a supervised hierarchy.

Do NOT build a fully connected agent swarm.

Top level:

PLATFORM SUPERVISOR

Below it:

DOMAIN MANAGERS

Below them:

DOMAIN SPECIALISTS.

Also implement independent oversight roles:

VERIFIER
RISK REVIEWER
COST ESTIMATOR
POLICY / APPROVAL GATE

Possible domain managers:

Infrastructure Advisor Manager
Data Manager
Process Manager
Security Manager
Cloud Manager
Customer Support Manager
Agent Engineering Manager

Specialist agents should have minimal tool permissions.

Read-only agents must not receive write tools.

Agents performing meaningful external side effects require an approval
boundary.

Every agent should have:

name,
purpose,
explicit responsibilities,
allowed tools,
forbidden tools/actions,
structured input schema,
structured output schema,
timeout,
tool-call limit,
retry policy,
cost/token limits where possible,
failure behavior,
escalation policy.

Use structured machine-to-machine communication.

Do not pass uncontrolled long natural-language conversations between
internal agents when typed objects can be used.

Agent outputs should distinguish:

facts,
evidence,
calculations,
assumptions,
inferences,
recommendations,
uncertainty,
required human decision.

Do not persist hidden chain-of-thought.

Persist appropriate operational information such as:

inputs,
outputs,
tool calls,
evidence,
decision summaries,
errors,
timings,
cost/usage,
approval events,
trace identifiers.

==================================================
MODULE H — AGENT FACTORY
==================================================

Create a controlled Agent Factory.

The Agent Factory should help users design additional agents when the
organization requires a new capability.

It should generate:

agent specification,
responsibility boundary,
tool requirements,
permission requirements,
structured schemas,
guardrails,
evaluation scenarios,
risk assessment,
test plan,
prompt/configuration proposal.

It must NOT autonomously give a newly generated agent unrestricted tools.

New agents go through:

DRAFT
VALIDATION
EVALUATION
HUMAN APPROVAL
ENABLED

Maintain version history.

A rejected version must remain auditable.

==================================================
MODULE I — CUSTOMER SUPPORT INTELLIGENCE
==================================================

Implement an enterprise customer-support assistant.

Use approved organizational knowledge.

Implement retrieval with tenant/company isolation.

Responses should provide evidence/citations to internal sources when possible.

The bot must:

avoid fabricating company policy,
recognize uncertainty,
escalate to humans,
respect user permissions,
avoid exposing restricted documents,
redact or minimize sensitive information where appropriate.

Provide:

FAQ handling,
knowledge search,
ticket classification,
suggested replies,
escalation,
support analytics,
feedback.

No autonomous external communication without appropriate approval.

==================================================
MODULE J — UNIVERSAL IN-APP ASSISTANT
==================================================

Every major part of the UI should expose contextual help.

The assistant must understand:

the page,
the module,
the user's role,
available actions,
relevant documentation.

Example:

A junior employee opens Data Cleaning and asks:
"What should I do here?"

The assistant should explain:

the purpose,
the current state,
next safe steps,
definitions,
how to perform the operation manually,
how AI-assisted mode works.

It should teach the user rather than merely perform everything for them.

==================================================
5. CONTINUOUS IMPROVEMENT — NOT UNSAFE SELF-MODIFICATION
==================================================

"Continuous learning" must NOT mean uncontrolled production self-modification.

Implement a controlled improvement lifecycle.

Collect:

explicit user feedback,
agent failures,
accepted/rejected recommendations,
support resolutions,
evaluation results.

Use these to create:

evaluation datasets,
prompt improvement proposals,
knowledge-base update proposals,
agent configuration proposals.

Changes must be versioned, tested and approved.

Do not let production agents silently rewrite their own system prompts,
permissions or tools.

==================================================
6. SECURITY ARCHITECTURE
==================================================

Security is a first-class domain requirement.

Implement:

authentication,
authorization,
RBAC,
tenant isolation,
least privilege,
secure sessions/tokens,
CSRF protection where applicable,
CORS policy,
security headers,
rate limiting,
input validation,
output encoding,
safe file upload handling,
file size/type limits,
malware scanning hook if practical,
secret management,
encrypted transport,
safe error messages,
secure logging,
audit logging.

Roles should include concepts such as:

platform administrator,
organization administrator,
data analyst,
process analyst,
security auditor,
cloud operator,
support agent,
viewer.

Use organization/tenant ownership throughout domain entities.

Evaluate PostgreSQL row-level security where it materially improves
tenant isolation.

Never store API keys in source control.

Provide:

.env.example

with safe placeholder values.

Ensure logs do not contain secrets.

Create an append-oriented audit trail for:

authentication events,
permission changes,
AI actions,
human approvals,
security scans,
cloud recommendations,
data transformations,
administrative actions.

Create:

docs/security/THREAT_MODEL.md
docs/security/TRUST_BOUNDARIES.md
docs/security/DATA_CLASSIFICATION.md
docs/security/INCIDENT_RESPONSE.md

Threat-model AI-specific risks including:

prompt injection,
indirect prompt injection,
tool abuse,
excessive permissions,
data leakage,
cross-tenant leakage,
malicious uploaded documents,
unsafe generated actions,
retrieval poisoning,
agent-to-agent propagation.

Treat retrieved documents as untrusted data,
not trusted instructions.

==================================================
7. DATABASE AND DATA MODEL
==================================================

Design proper normalized persistence.

Avoid a single generic JSON table for the entire application.

Use JSONB only where flexible schemas genuinely justify it.

Important entities may include:

Organization
User
Role
Permission
Project
CompanyProfile
InfrastructureAsset
CloudResource
Dataset
DatasetVersion
DataProfile
Transformation
Analysis
Process
ProcessEvent
ProcessAnalysis
SecurityTarget
SecurityScan
SecurityFinding
Remediation
Recommendation
Decision
CostEstimate
AgentDefinition
AgentVersion
AgentRun
ToolInvocation
ApprovalRequest
KnowledgeDocument
SupportConversation
SupportTicket
AuditEvent

Use migrations.

Use foreign keys.

Use sensible indexes.

Document major entity relationships.

==================================================
8. API DESIGN
==================================================

Provide versioned APIs such as:

/api/v1/

Use proper HTTP semantics.

Use Pydantic/typed validation.

Provide clear errors.

Implement pagination.

Implement filtering/sorting where needed.

Create OpenAPI documentation.

Do not expose internal ORM objects directly.

Use explicit request/response DTOs.

Generate or maintain frontend API types from backend contracts where practical.

==================================================
9. JOB EXECUTION
==================================================

Long-running operations must not block HTTP request workers.

Examples:

data profiling,
security scanning,
large analysis,
report generation,
agent evaluation,
cloud inventory.

Use background jobs.

Represent jobs with states such as:

QUEUED
RUNNING
WAITING_FOR_APPROVAL
SUCCEEDED
FAILED
CANCELLED

Expose progress and useful logs.

Implement retry behavior carefully.

Actions with side effects must be idempotent.

Use unique task/action identifiers.

==================================================
10. FRONTEND DESIGN
--------------------------------------------------

The UI must look like a serious enterprise engineering platform.

AVOID:

generic glowing AI gradients,
random neon colors,
excessive glassmorphism,
floating AI or brain icons,
decorative animations,
marketing-page appearance,
oversized cards containing little information.

Prefer:

clean information architecture,
professional typography,
consistent spacing,
strong tables,
filters,
search,
side navigation,
command/search functionality,
status indicators,
audit views,
dense but readable dashboards,
excellent empty/error/loading states.

The UI should feel closer to:

an engineering console,
analytics product,
cloud management portal,
or enterprise operations platform

than a consumer AI chatbot.

AI chat is a capability,
not the visual identity of the entire product.

Create a small internal design system.

Support desktop well.

Make responsive behavior functional.

Accessibility matters.

==================================================
11. EXPLAINABILITY
==================================================

This repository is intended to be learned and defended by its owner.

Therefore create human-readable explanations.

Every major module should include:

README.md
EXPLAIN.md
TESTING.md

EXPLAIN.md must answer:

- What problem does this module solve?
- Why was this architecture chosen?
- What are the important classes/functions?
- What is the request/data flow?
- What database tables does it use?
- What would fail if component X went down?
- What tradeoffs were made?
- How can the owner modify it?
- What interview/IHK questions could be asked about it?

Use comments to explain WHY,
not obvious syntax.

Use type hints.

Use docstrings for public interfaces.

Create Mermaid architecture diagrams where useful.

Maintain Architecture Decision Records.

==================================================
12. IHK / PROFESSIONAL DOCUMENTATION
==================================================

Create an IHK-oriented documentation area that explains the engineering
without falsely claiming work that was not actually performed by the owner.

Suggested material:

project context,
business problem,
current-state analysis,
target-state concept,
requirements,
stakeholders,
technical alternatives,
economic evaluation,
utility/value analysis,
architecture decision,
risk analysis,
security considerations,
data protection considerations,
project plan,
testing strategy,
acceptance criteria,
results,
lessons learned.

Clearly mark templates as templates.

Do not fabricate company facts, working hours, costs or decisions.

==================================================
13. TEST ENGINEERING
==================================================

Testing is a core deliverable.

Create:

unit tests,
integration tests,
API tests,
database tests,
agent/tool contract tests,
authorization tests,
tenant-isolation tests,
frontend component tests where justified,
end-to-end tests,
security regression tests.

Use Playwright or equivalent for important end-to-end frontend workflows.

Use property-based testing where it creates actual value.

Provide deterministic tests.

AI tests must not depend entirely on probabilistic exact-string matching.

Create agent evaluations.

Evaluate:

routing,
tool selection,
structured output validity,
permission compliance,
unsupported claims,
evidence use,
cost,
latency,
failure recovery.

Create synthetic enterprise scenarios such as:

small cost-focused company,
high-performance technical company,
regulated organization,
manufacturing company,
cloud-native company,
legacy hybrid organization.

Include representative datasets.

No sensitive real-world information.

==================================================
14. SECURITY TEST ENVIRONMENT
==================================================

Create an explicit Docker Compose security-lab profile if appropriate.

Use intentionally vulnerable local applications only.

Keep them isolated.

Never expose them publicly by default.

The platform should demonstrate:

scan request,
authorization/scope validation,
scanner execution,
evidence collection,
finding normalization,
AI interpretation,
human review,
remediation advice,
rescan,
finding closure.

This end-to-end workflow is more important than adding many scanners.

==================================================
15. FAILURE AND CHAOS TESTS
==================================================

Test realistic failures.

Examples:

database unavailable,
Redis unavailable,
LLM API unavailable,
LLM rate limit,
invalid model response,
malformed tool output,
scanner timeout,
corrupt uploaded dataset,
oversized file,
unauthorized target,
cancelled job,
frontend API timeout.

The application must fail safely.

AI unavailability should not corrupt core business state.

==================================================
16. PERFORMANCE
==================================================

Measure important flows.

Avoid loading huge datasets into web workers.

Use streaming/chunking where appropriate.

Introduce query limits.

Add indexes based on query behavior.

Provide load-test scenarios for important APIs.

Document performance assumptions.

==================================================
17. OBSERVABILITY
==================================================

Implement:

structured logs,
request IDs,
job IDs,
agent run IDs,
metrics,
health checks,
readiness checks.

Allow correlation of:

user request
-> API request
-> job
-> agent run
-> tool invocation
-> result.

Never expose sensitive prompts/data through diagnostics without an explicit
configuration.

==================================================
18. PORTABILITY
==================================================

The complete project must be usable from a clean machine.

Provide Docker support.

At minimum create:

Dockerfile(s)
docker-compose.yml
docker-compose.override.yml if useful
.dockerignore
.env.example

Use multi-stage Docker builds where sensible.

Do not require the developer to manually install PostgreSQL or Redis.

The core development stack should start with something equivalent to:

docker compose up --build

Provide health checks.

Support Linux.

Keep host assumptions minimal so that Docker Desktop on Windows/macOS
can run the project.

Build architecture suitable for:

linux/amd64
linux/arm64

where dependencies permit it.

Do not hard-code filesystem paths.

--------------------------------------------------
19. DEVELOPMENT ENVIRONMENTS
--------------------------------------------------

Design explicit environments/profiles:

development
test
demo
security-lab
production-template

Do not mix deliberately vulnerable security-lab services with production
profiles.

--------------------------------------------------
20. CI/CD
--------------------------------------------------

Create GitHub Actions.

The pipeline should include appropriate combinations of:

format check,
lint,
type check,
unit tests,
integration tests,
frontend tests,
build,
dependency audit,
secret scan,
container scan,
Docker build.

Use caching appropriately.

Never require production secrets for pull-request tests.

Use deterministic/mock AI provider in CI.

Provide an optional live-AI integration/evaluation workflow requiring
explicit secrets.

--------------------------------------------------
21. GITHUB REPOSITORY QUALITY
--------------------------------------------------

Create professional repository files:

README.md
CONTRIBUTING.md
SECURITY.md
CHANGELOG.md
CODEOWNERS if appropriate
.gitignore
.editorconfig
pre-commit configuration if appropriate

README must include:

what the project is,
architecture overview,
screenshots section,
feature status,
quick start,
Docker usage,
configuration,
test instructions,
security notice,
project structure,
documentation links.

Do not advertise unfinished features as finished.

--------------------------------------------------
22. LOCAL DEMO
--------------------------------------------------

Provide a reproducible demo organization.

Seed:

company profile,
sample users/roles,
sample infrastructure,
sample dataset,
sample process,
sample customer-support documentation,
sample security-lab target.

The reviewer should be able to run the platform and demonstrate
end-to-end workflows without manually constructing everything.

Do NOT use real customer information.

--------------------------------------------------
23. ACCEPTANCE WORKFLOWS
--------------------------------------------------

At minimum these end-to-end workflows must eventually work:

WORKFLOW 1:
Create company
-> enter requirements
-> run architecture assessment
-> compare IaaS/PaaS/SaaS/hybrid alternatives
-> receive explainable recommendation
-> view cost/performance decision matrix.

WORKFLOW 2:
Upload dataset
-> profile it
-> inspect quality problems
-> manually/AI-create cleaning plan
-> preview
-> apply
-> visualize
-> export analysis.

WORKFLOW 3:
Analyze operational data
-> detect process bottleneck
-> calculate process metrics
-> propose improved process
-> generate comparison diagram.

WORKFLOW 4:
Register authorized security-lab target
-> run safe assessment
-> normalize findings
-> prioritize findings
-> receive remediation guidance
-> mark remediation
-> rescan.

WORKFLOW 5:
Create cloud architecture scenario
-> calculate resilience requirements
-> define backup/DR
-> define RBAC
-> create cost/FinOps recommendations
-> generate architecture report.

WORKFLOW 6:
Customer asks support question
-> retrieve authorized knowledge
-> provide grounded answer
-> escalate when uncertain
-> record feedback.

WORKFLOW 7:
User requests new AI agent
-> Agent Factory creates specification
-> verifier checks it
-> risk reviewer checks permissions
-> evaluation suite runs
-> human approves
-> agent version becomes enabled.

--------------------------------------------------
24. QUALITY GATES
--------------------------------------------------

A module is not COMPLETE merely because an endpoint exists.

A module becomes complete only when relevant:

business logic,
persistence,
authorization,
validation,
API,
UI,
tests,
error handling,
logging,
documentation

exist and its important end-to-end workflow passes.

--------------------------------------------------
25. IMPLEMENTATION STRATEGY
--------------------------------------------------

Do not attempt to create thousands of lines in one uncontrolled pass.

Work iteratively.

However, do not stop merely because the project is large.

Create a milestone plan and continue through it.

Recommended order:

foundation and architecture;
identity/RBAC/multi-tenancy;
company intake;
decision engine;
agent runtime;
data intelligence;
process intelligence;
cloud/FinOps;
security lab;
support/RAG;
agent factory;
cross-module assistant;
observability;
hardening;
performance;
full evaluation.

You may change this order if dependencies justify it.

Implement vertical slices rather than large layers of unused abstractions.

--------------------------------------------------
26. ENGINEERING REVIEW LOOP
--------------------------------------------------

For every milestone perform a self-review using separate perspectives:

ARCHITECT REVIEW:
Does this architecture remain coherent?

SECURITY REVIEW:
Did the change create a trust-boundary or permission problem?

DATA REVIEW:
Are data contracts and lineage correct?

QA REVIEW:
What failure modes are missing from the tests?

OPERATIONS REVIEW:
Can this run and be diagnosed in a real environment?

MAINTAINABILITY REVIEW:
Would another engineer understand and safely change this?

Do not merely write reviews.

Fix the problems the reviews discover.

--------------------------------------------------
27. FINAL DEFINITION OF DONE
--------------------------------------------------

The project is successful when a technical reviewer can:

clone the Git repository;
configure environment variables;
run it with Docker;
open the frontend;
authenticate;
use the demo organization;
execute meaningful workflows;
inspect real persisted results;
inspect agent traces/audit records;
run tests;
understand the architecture;
read the documentation;
modify a module;
and see that the system was designed intentionally rather than generated
as a superficial demo.

At all times prioritize engineering substance over visual spectacle.
