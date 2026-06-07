# Overview

<!-- record:rec_generated_projections_read_only_5aa0e24efcc0 -->
## Generated projections are read-only

**ID:** `rec_generated_projections_read_only_5aa0e24efcc0`  
**Key:** `generated_projections_read_only`  
**Type:** `constraint` | **Status:** `active` | **Verification:** `verified`  

Markdown views and the agent bootstrap must be regenerated from canonical JSON.

**Constraint:** Do not edit generated Markdown views or agent-bootstrap.json as source data.  
**Consequences:**
- Regenerate projections with render, bootstrap, or build.
- Discard projection-only changes that are not represented in memory.json.

**Evidence:**
- `src_skill_md_ee1fe041d607`: supports via direct_observation

<!-- record:rec_controlled_mutation_pipeline_ba2150c97e21 -->
## Controlled memory mutation pipeline

**ID:** `rec_controlled_mutation_pipeline_ba2150c97e21`  
**Key:** `controlled_mutation_pipeline`  
**Type:** `implementation_detail` | **Status:** `active` | **Verification:** `verified`  

The CLI manages source registration, runs, record lifecycle, validation, and projection builds.

**Detail:** Canonical writes flow through add-source, start-run, add-record or update-record or supersede-record, finish-run, and build.  
**Components:**
- add-source
- start-run
- add-record
- update-record
- supersede-record
- finish-run
- validate
- render
- bootstrap
- build

**Evidence:**
- `src_kiroku_py_32b19fd05327`: supports via direct_observation

<!-- record:rec_single_active_run_99767010fee9 -->
## Single active mutation run

**ID:** `rec_single_active_run_99767010fee9`  
**Key:** `single_active_run`  
**Type:** `constraint` | **Status:** `active` | **Verification:** `verified`  

Only one run may be active and build waits for its completion.

**Constraint:** A memory may contain at most one running run, and projections must not be built until it is completed.  
**Consequences:**
- Concurrent mutations are serialized.
- Published projections cannot represent a partially completed operation.

**Evidence:**
- `src_validation_py_c4831a31501b`: supports via direct_observation

<!-- record:rec_optimistic_record_updates_45cfab2c03b2 -->
## Optimistic record updates

**ID:** `rec_optimistic_record_updates_45cfab2c03b2`  
**Key:** `optimistic_record_updates`  
**Type:** `implementation_detail` | **Status:** `active` | **Verification:** `verified`  

Record replacement requires the current content hash and preserves stable identity.

**Detail:** update-record performs complete semantic replacement only when --expect-hash matches, preserving id, key, type, and created_at while refreshing updated_at, generated_by, and content_hash.  
**Components:**
- record draft normalization
- semantic comparison
- expected hash check
- atomic canonical write

**Evidence:**
- `src_records_py_c238f9857c74`: supports via direct_observation
- `src_kiroku_py_32b19fd05327`: supports via direct_observation

<!-- record:rec_p0_controlled_writes_complete_fb377628b080 -->
## P0 controlled writes complete

**ID:** `rec_p0_controlled_writes_complete_fb377628b080`  
**Key:** `p0_controlled_writes_complete`  
**Type:** `fact` | **Status:** `active` | **Verification:** `verified`  

The controlled write core is implemented and verified at commit e598905.

**Statement:** At commit e598905, KirokuForge implements controlled sources, run lifecycle, record creation, optimistic updates, atomic supersession, validation, rendering, and bootstrap generation; 62 tests pass.

**Evidence:**
- `src_kiroku_forge_cd2b9cf4fc73`: supports via test_result
- `src_kiroku_forge_p0_8f0086c3a328`: context via direct_observation

