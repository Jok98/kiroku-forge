# Decisions

<!-- record:rec_canonical_json_memory_a72909b99be1 -->
## Canonical JSON memory

**ID:** `rec_canonical_json_memory_a72909b99be1`  
**Key:** `canonical_json_memory`  
**Type:** `decision` | **Status:** `active` | **Verification:** `verified`  

memory.json is the only editable source of truth.

**Decision:** Use kiroku/memory.json as the canonical project-memory artifact.  
**Context:** Agents and user-facing projections need one authoritative representation.  
**Implications:**
- Generated Markdown and bootstrap files are projections.
- Canonical mutations must validate against the memory schema.

**Evidence:**
- `src_skill_md_ee1fe041d607`: supports via direct_observation

<!-- record:rec_provenance_backed_claims_a3ab965374ab -->
## Provenance-backed durable claims

**ID:** `rec_provenance_backed_claims_a3ab965374ab`  
**Key:** `provenance_backed_claims`  
**Type:** `decision` | **Status:** `active` | **Verification:** `verified`  

Durable memory distinguishes observed evidence from inference.

**Decision:** Attach structured source evidence to durable claims and preserve explicit uncertainty.  
**Context:** Future agents must understand both what is believed and why.  
**Implications:**
- Verified claims require direct supporting evidence.
- Inferences remain distinguishable from observations.
- Sources use stable locators, revisions, and hashes when available.

**Evidence:**
- `src_skill_md_ee1fe041d607`: supports via direct_observation

<!-- record:rec_linear_supersession_history_39b69a2cd188 -->
## Linear supersession history

**ID:** `rec_linear_supersession_history_39b69a2cd188`  
**Key:** `linear_supersession_history`  
**Type:** `decision` | **Status:** `active` | **Verification:** `verified`  

Historical replacement uses one predecessor and one direct successor without cycles.

**Decision:** Preserve replaced knowledge through atomic linear supersession chains.  
**Context:** Historical claims must remain inspectable without allowing ambiguous replacement graphs.  
**Implications:**
- A superseded record has exactly one direct replacement.
- A replacement supersedes exactly one direct predecessor.
- Branches, merges, cycles, and later edits to historical predecessors are rejected.

**Evidence:**
- `src_validation_py_c4831a31501b`: supports via direct_observation
- `src_kiroku_py_32b19fd05327`: supports via direct_observation

<!-- record:rec_version_control_independent_operation_eec90a915833 -->
## Version-control independent operation

**ID:** `rec_version_control_independent_operation_eec90a915833`  
**Key:** `version_control_independent_operation`  
**Type:** `decision` | **Status:** `active` | **Verification:** `verified`  

KirokuForge treats source revisions as opaque identifiers and does not invoke version-control tools.

**Decision:** Keep KirokuForge independent from Git and all other version-control systems.  
**Context:** Memory storage and source verification must work for local, external, or independently managed artifacts.  
**Implications:**
- Revision values are opaque identifiers supplied by the user or agent.
- The CLI validates captured hashes and internal consistency without resolving external revisions.
- Versioning, backup, and synchronization remain outside the skill boundary.

**Evidence:**
- `src_session_2026_06_07_architecture_6ceac687ec54`: supports via user_statement
- `src_skill_md_dec324b6ab2b`: supports via direct_observation

<!-- record:rec_kiroku_forge_development_memory_db47fef3a4c6 -->
## Maintain KirokuForge development memory

**ID:** `rec_kiroku_forge_development_memory_db47fef3a4c6`  
**Key:** `kiroku_forge_development_memory`  
**Type:** `decision` | **Status:** `active` | **Verification:** `verified`  

The project-local kiroku directory is the official durable memory for development of the skill itself.

**Decision:** Maintain kiroku/ in this project as the official development memory for KirokuForge.  
**Context:** The skill is developed using its own memory model so decisions, milestones, evidence, and rationale remain reusable across sessions.  
**Implications:**
- Update canonical memory at the end of meaningful development sessions.
- Regenerate projections from memory.json after each update.
- This dogfooding choice does not prescribe where other users store their memories.

**Evidence:**
- `src_session_2026_06_07_architecture_6ceac687ec54`: supports via user_statement

