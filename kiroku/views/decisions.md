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

