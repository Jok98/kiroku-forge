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

