# Actions

<!-- record:rec_agent_query_command_completed_56db657db32c -->
## Add selective agent queries

**ID:** `rec_agent_query_command_completed_56db657db32c`  
**Key:** `agent_query_command_completed`  
**Type:** `roadmap_item` | **Status:** `completed` | **Verification:** `verified`  

The query command is implemented with filters for key, type, status, scope, tag, relation-target, and relation-type, with sorting and multiple output formats.

**Outcome:** The query command supports filtering by key, type, status, scope, tag, relation-target, and relation-type, combined as a single relation when both target and type are specified. Enum validation rejects unknown values. Output formats: compact, full, ids. Sorting by title, type, status, created_at, updated_at (datetime). --count flag.  
**Horizon:** now  
**Priority:** high

**Evidence:**
- `src_test_query_cli_py_2b278b258c11`: supports via direct_observation
- `src_kiroku_forge_query_v2_768d745bae26`: supports via test_result
- `src_kiroku_py_c043f2f57ea3`: supports via direct_observation

<!-- record:rec_p1_agent_efficiency_complete_715ed9381da4 -->
## Complete P1 agent efficiency

**ID:** `rec_p1_agent_efficiency_complete_715ed9381da4`  
**Key:** `p1_agent_efficiency_complete`  
**Type:** `roadmap_item` | **Status:** `completed` | **Verification:** `verified`  

Selective queries, compact bootstrap output, and incremental source checks are implemented and verified.

**Outcome:** P1 provides compact agent context, selective record queries, and read-only incremental source detection through content hashes, without depending on external version-control systems.  
**Horizon:** now  
**Priority:** high

**Evidence:**
- `src_skill_md_dec324b6ab2b`: supports via direct_observation
- `src_kiroku_forge_p1_final_0f883bb65893`: supports via test_result
- `src_session_2026_06_07_architecture_6ceac687ec54`: supports via user_statement

<!-- record:rec_p2_local_memory_viewer_complete_634e5368c5c6 -->
## Complete P2 local memory viewer

**ID:** `rec_p2_local_memory_viewer_complete_634e5368c5c6`  
**Key:** `p2_local_memory_viewer_complete`  
**Type:** `roadmap_item` | **Status:** `completed` | **Verification:** `verified`  

The read-only local viewer, API, interactive explorer, and provenance details are implemented and verified.

**Outcome:** P2 provides reusable shared queries, a loopback-only read-only API over canonical memory, and a dependency-free browser UI with dashboard, complete record filters, stable deep links, provenance, relations, sources, and run history.  
**Horizon:** now  
**Priority:** high

**Evidence:**
- `src_viewer_contract_md_1bddba144dbe`: supports via direct_observation
- `src_viewer_py_2c3103427c7e`: supports via direct_observation
- `src_app_js_b57b6335d85e`: supports via direct_observation
- `src_test_viewer_server_py_da2162e203af`: supports via direct_observation
- `src_p2_2_verification_607a563f11b1`: supports via test_result

