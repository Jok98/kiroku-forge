# Actions

<!-- record:rec_agent_query_command_6b4bb1d09eb1 -->
## Add selective agent queries

**ID:** `rec_agent_query_command_6b4bb1d09eb1`  
**Key:** `agent_query_command`  
**Type:** `roadmap_item` | **Status:** `superseded` | **Verification:** `unverified`  

The next efficiency capability is filtered record retrieval without loading all canonical memory.

**Outcome:** Provide a query command for key, type, status, scope, tag, and relation filters with compact structured output.  
**Horizon:** next  
**Priority:** high

**Evidence:**
- `src_kiroku_py_32b19fd05327`: context via inference

<!-- record:rec_agent_query_command_completed_56db657db32c -->
## Add selective agent queries

**ID:** `rec_agent_query_command_completed_56db657db32c`  
**Key:** `agent_query_command_completed`  
**Type:** `roadmap_item` | **Status:** `completed` | **Verification:** `verified`  

The query command is implemented with filters for key, type, status, scope, tag, relation-target, and relation-type, with sorting and multiple output formats.

**Outcome:** The query command supports filtering by key, type, status, scope, tag, relation-target, and relation-type. Output formats: compact, full, ids. Sorting by title, type, status, created_at, updated_at. --count flag.  
**Horizon:** now  
**Priority:** high

**Evidence:**
- `src_test_query_cli_py_8b0feb2a33c0`: supports via direct_observation
- `src_kiroku_forge_query_522b99efed65`: supports via test_result
- `src_kiroku_py_32b19fd05327`: context via direct_observation

