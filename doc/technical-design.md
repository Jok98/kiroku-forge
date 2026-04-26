# KirokuForge MVP Technical Design

## 1. Product Definition

KirokuForge is a local-first, Git-native, developer-first CLI that turns AI-assisted work sessions into structured, reviewed, versioned Markdown project knowledge.

The CLI binary is:

```bash
kiroku
```

The standard knowledge repository name is:

```text
kirokuforge-knowledge
```

The published source of truth is a Git repository containing reviewed Markdown artifacts. Raw conversations may exist only as local transient/session state and must never be committed.

The core product flow is:

```text
User starts a project session
-> user works with AI
-> user runs /save or kiroku save
-> Knowledge Processing Agent extracts useful knowledge
-> KirokuForge proposes Markdown artifacts
-> user reviews/edits them
-> KirokuForge pulls latest main
-> KirokuForge writes files
-> KirokuForge shows diff
-> user confirms
-> KirokuForge commits
-> KirokuForge pushes
```

The architecture distinguishes two AI roles:

- Chat Assistant: helps during the interactive session with reasoning, writing, debugging, design, and analysis.
- Knowledge Processing Agent: post-processes the session into durable project knowledge.

The Knowledge Processing Agent is intentionally separate from the Chat Assistant. It may propose artifacts and commit messages, but it must not commit, push, silently overwrite files, save raw conversation, invent decisions, or resolve semantic conflicts without the user.

## 2. Business Rules

- KirokuForge must not require a SaaS backend.
- Git is the source of truth for published project knowledge.
- Raw conversations must never be committed to Git.
- Only reviewed, structured Markdown artifacts may be written to the knowledge repository.
- Every generated artifact requires explicit user review before writing.
- Every commit requires explicit user confirmation.
- Every remote write must be preceded by `git pull --rebase origin main`.
- Git remotes are provider-agnostic and must work with GitHub, GitLab, Gitea, Bitbucket, and any remote supported by Git.
- KirokuForge must use the user's local Git, SSH agent, and credential helpers.
- KirokuForge must use pure Git CLI operations as the primary Git implementation.
- KirokuForge must not depend on GitHub CLI.
- If `git ls-remote <remote-url>` fails, KirokuForge must print exactly: `Repository not found or inaccessible.`
- KirokuForge must not infer whether a failed remote check is caused by a missing repository, missing permissions, broken SSH, or network failure.
- If the remote is unreachable, the user must manually create a repository named `kirokuforge-knowledge` on their Git provider.
- After user confirmation, KirokuForge must re-run `git ls-remote`.
- If the repository is empty or missing `kirokuforge.yml`, KirokuForge must ask whether to initialize the repository structure.
- KirokuForge must never silently overwrite remote content.
- Git conflicts require human-in-the-loop resolution.
- Secrets, API keys, tokens, and private credentials must be redacted before artifact review.
- Artifact target paths must stay under `projects/<project-slug>/`.
- No file write is allowed without user approval.
- No commit is allowed without user approval.
- No push is allowed while unresolved conflicts exist.

## 3. Command List And CLI UX

The first working version provides these commands:

```bash
kiroku init
kiroku repo status
kiroku sync
kiroku project create <project-name>
kiroku project list
kiroku chat <project-name>
kiroku save <project-name>
kiroku diff [project-name]
kiroku conflict list
kiroku conflict resolve
kiroku auth login
kiroku auth list
kiroku models list
kiroku models use <provider:model>
```

Interactive flows should use JLine. Prompts must make destructive or publishing actions explicit and default to safe answers.

Examples:

```text
Write these 3 artifacts to the knowledge repository? [y/N]
Commit changes with message "docs(api): record retry strategy decision"? [y/N]
Push commit to origin/main? [y/N]
```

Slash commands inside `kiroku chat <project-name>`:

```text
/save
/diff
/sync
/project
/exit
/help
```

Exit codes:

```text
0 success
1 generic error
2 invalid command/input
3 git not configured
4 repository dirty
5 sync conflict
6 AI provider error
7 user aborted
8 authentication error
9 repository not found or inaccessible
```

## 4. Repository Layout

The standard knowledge repository layout is:

```text
kirokuforge-knowledge/
├── README.md
├── kirokuforge.yml
├── projects/
│   ├── example-project/
│   │   ├── overview.md
│   │   ├── architecture/
│   │   ├── decisions/
│   │   ├── notes/
│   │   ├── open-questions/
│   │   └── todo/
│   └── another-project/
└── templates/
    ├── decision.md
    ├── architecture.md
    ├── note.md
    ├── todo.md
    └── open-question.md
```

Repository manifest:

```yaml
version: 1

repository:
  type: kirokuforge-knowledge
  default_branch: main

layout:
  projects_dir: projects
  templates_dir: templates

rules:
  raw_conversations_allowed: false
  pull_before_write: true
  require_user_review_before_commit: true
  conflict_resolution: human_in_the_loop
```

## 5. Git Workflow

KirokuForge uses Git CLI through `ProcessBuilder`.

Required Git commands:

```bash
git ls-remote <remote-url>
git clone <remote-url> <local-path>
git fetch origin
git pull --rebase origin main
git status --porcelain
git diff
git add <files>
git commit -m "<message>"
git push origin main
```

Remote mode rules:

- Check remote reachability before clone.
- Clone only after `git ls-remote <remote-url>` succeeds.
- Run `git fetch origin` and `git pull --rebase origin main` before every write.
- Stop on conflicts and tell the user to run `kiroku conflict resolve`.
- Do not write generated files into a conflicted working tree.
- Do not commit if validation fails.
- Do not push until the user confirms.

Local-only mode rules:

- Initialize a local Git repository.
- Initialize the same KirokuForge repository structure.
- Use the same validation, review, diff, and commit flow.
- Skip remote reachability, fetch, pull, and push.

## 6. Init Workflow

`kiroku init` initializes local KirokuForge configuration and the knowledge repository.

Local config paths on Linux:

```text
~/.config/kirokuforge/config.yml
~/.local/share/kirokuforge/kirokuforge.db
~/.local/share/kirokuforge/auth.json
~/.cache/kirokuforge/
~/KirokuForge/kirokuforge-knowledge/
```

Remote Git mode:

1. Create local config directory.
2. Ask whether to use remote Git mode or local-only mode.
3. Ask for remote URL.
4. Run `git ls-remote <remote-url>`.
5. If unreachable, print `Repository not found or inaccessible.`
6. Ask the user to manually create a repository named `kirokuforge-knowledge`.
7. After confirmation, retry `git ls-remote <remote-url>`.
8. Clone with `git clone <remote-url> <local-path>`.
9. If `kirokuforge.yml` is missing, ask whether to initialize KirokuForge structure.
10. Create `README.md`, `kirokuforge.yml`, `projects/`, and `templates/`.
11. Commit the initial structure.
12. Push to `origin main`.

Local-only mode:

1. Create local config directory.
2. Create `~/KirokuForge/kirokuforge-knowledge/`.
3. Run `git init`.
4. Create the KirokuForge structure.
5. Create the initial commit.
6. Do not require or configure a remote.

## 7. Project Workflow

`kiroku project create <project-name>` creates a project knowledge area.

Slug rules:

- Lowercase.
- Replace spaces and separators with `-`.
- Remove unsafe path characters.
- Reject empty slugs.
- Reject `.` and `..`.
- Reject path traversal.

Generated structure:

```text
projects/<project-slug>/
├── overview.md
├── architecture/
├── decisions/
├── notes/
├── open-questions/
└── todo/
```

Commit message:

```text
docs(<project-slug>): initialize project knowledge base
```

Remote mode behavior:

1. Run `git fetch origin`.
2. Run `git pull --rebase origin main`.
3. Create project files.
4. Run `git diff`.
5. Ask for confirmation.
6. Commit and push.

Local-only behavior:

1. Create project files.
2. Run `git diff`.
3. Ask for confirmation.
4. Commit locally.

`kiroku project list` lists available projects under `projects/`.

## 8. Chat Workflow

`kiroku chat <project-name>` starts an interactive AI session.

Responsibilities:

- Resolve the project by slug or name.
- Start a local `ChatSession`.
- Load project context.
- Load relevant existing knowledge context.
- Send user messages to the selected Chat Assistant provider.
- Stream assistant responses when the provider supports streaming.
- Support slash commands.
- Keep raw messages local only.

The session may be stored in SQLite for resumability, but session data must not be written into the knowledge repository.

The Chat Assistant helps the user work. It does not decide what durable knowledge is saved. Durable knowledge is produced only by the Knowledge Processing Agent during `kiroku save` or `/save`.

## 9. Save Workflow

`kiroku save <project-name>` processes the current or selected session.

Pipeline:

1. Load session context.
2. Load project context.
3. Load existing knowledge tree.
4. Run the Knowledge Processing Agent.
5. Produce a `SummaryCandidate`.
6. Show generated artifacts, warnings, target paths, confidence, and proposed commit message.
7. Ask the user to review the artifacts.
8. Allow edit, regenerate, discard, or approve.
9. Validate approved artifacts.
10. Run `git fetch origin` and `git pull --rebase origin main` in remote mode.
11. Write approved Markdown files.
12. Show `git diff`.
13. Ask for commit confirmation.
14. Run `git add <files>`.
15. Run `git commit -m "<message>"`.
16. Ask for push confirmation in remote mode.
17. Run `git push origin main`.

Abort conditions:

- No active or selected session exists.
- No reviewed artifacts are approved.
- Artifact validation fails.
- Working tree contains unrelated dirty changes that would make the operation unsafe.
- Pull/rebase produces conflicts.
- AI provider fails.
- User aborts review, write, commit, or push.

## 10. Knowledge Processing Agent Design

The Knowledge Processing Agent is a dedicated post-processing agent. It transforms a session into durable knowledge and outputs a machine-parseable `SummaryCandidate`.

Conceptual pipeline:

```text
SessionContext
-> SignalExtractor
-> KnowledgeClassifier
-> ArtifactRouter
-> ArtifactGenerator
-> ArtifactValidator
-> CommitPlanner
-> SummaryCandidate
```

Responsibilities:

- Extract durable knowledge from the session.
- Ignore conversational noise.
- Extract decisions.
- Extract TODOs.
- Extract open questions.
- Extract alternatives considered.
- Extract architecture notes.
- Classify artifact types.
- Route content to target files.
- Generate Markdown.
- Propose commit messages.
- Validate that raw conversation is not being saved.
- Prepare a `SummaryCandidate` for user review.

The agent must not:

- Commit directly.
- Push directly.
- Silently overwrite files.
- Save raw conversation.
- Invent decisions.
- Resolve semantic conflicts without the user.

Prompt rules:

```text
Do not preserve raw conversation.
Do not write "the user said" or "the assistant replied".
Extract only durable project knowledge.
Prefer concise technical documentation.
Preserve decisions, tradeoffs, TODOs and open questions.
If information is uncertain, put it under Open Questions.
Never invent decisions.
Never expose secrets, API keys, tokens or private credentials.
Route each artifact to the correct project folder.
Output must be structured and machine-parseable.
```

Recommended structured output:

```json
{
  "artifacts": [
    {
      "type": "decision",
      "targetPath": "projects/example-project/decisions/2026-04-26-use-git-as-source-of-truth.md",
      "title": "Use Git as the source of truth for knowledge",
      "markdownContent": "...",
      "confidence": 0.91,
      "operation": "CREATE"
    }
  ],
  "commitMessage": "docs(example-project): record Git-backed knowledge decisions",
  "warnings": [],
  "requiresReview": true
}
```

Validation rules:

- Target path must be under `projects/<project-slug>/`.
- Raw conversation phrases must be rejected.
- Secrets must be redacted.
- Required frontmatter must exist.
- Required sections must exist.
- File write requires user approval.
- Commit requires user approval.
- Push is blocked if unresolved conflicts exist.

## 11. LLM Provider Architecture

Provider interface:

```java
public interface LlmProvider {
    ProviderId id();
    AuthStatus authStatus();
    List<ModelDescriptor> listModels();
    LlmResponse complete(LlmRequest request);
    Stream<LlmChunk> stream(LlmRequest request);
}
```

MVP providers:

- `openai-codex`
- `openai-api`
- `ollama`

`openai-codex` rules:

- Use official Codex CLI integration.
- Support users with ChatGPT subscription but no OpenAI API key.
- Do not scrape ChatGPT.
- Do not steal browser cookies.
- Do not read undocumented private token files.
- Delegate authentication and model access to official Codex CLI flows.

`openai-api` rules:

- Use an OpenAI API key.
- Treat API key configuration as optional.
- Store credentials locally.
- Prefer system keyring when available.
- Fall back to `auth.json` with restricted file permissions.

`ollama` rules:

- Use local Ollama server.
- Require no cloud login.
- List models from the local Ollama API when available.

Model commands:

```bash
kiroku models list
kiroku models use <provider:model>
```

Examples:

```bash
kiroku models use openai-codex:gpt-5.1-codex
kiroku models use ollama:llama3.1
```

## 12. Local Persistence Model

SQLite stores local operational state. It is not the published knowledge store.

Core entities:

- `Project`
- `KnowledgeRepository`
- `ChatSession`
- `KnowledgeSignal`
- `SummaryCandidate`
- `ArtifactCandidate`
- `MergeConflict`

Raw messages may be persisted locally for resumability, but must be marked as local-only and excluded from Git.

Domain entity summaries:

```text
Project
- id
- name
- slug
- description
- localPath
- createdAt

KnowledgeRepository
- localPath
- remoteUrl
- defaultBranch
- mode: REMOTE or LOCAL_ONLY

ChatSession
- id
- projectId
- startedAt
- endedAt
- status
- transient messages or local-only session data

KnowledgeSignal
- type
- content
- confidence
- rationale

SummaryCandidate
- id
- projectId
- artifacts
- commitMessage
- warnings
- requiresReview

ArtifactCandidate
- type
- targetPath
- title
- markdownContent
- confidence
- operation: CREATE, UPDATE, APPEND

MergeConflict
- id
- projectId
- filePath
- localVersion
- remoteVersion
- baseVersion
- aiSuggestion
- status
```

## 13. Markdown Templates

Default artifact format:

```markdown
---
project: <project-slug>
type: <architecture|decision|note|todo|open-question>
status: draft
created_at: <yyyy-mm-dd>
updated_at: <yyyy-mm-dd>
tags:
  - <tag>
---

# <Title>

## Summary

## Key Points

## Decisions

## Alternatives Considered

## Open Questions

## TODO

## Related Files
```

Template files:

```text
templates/decision.md
templates/architecture.md
templates/note.md
templates/todo.md
templates/open-question.md
```

Recommended file naming:

```text
yyyy-mm-dd-short-title.md
```

Example:

```text
projects/payments/decisions/2026-04-26-use-git-as-knowledge-source.md
```

Artifact type routing:

- `architecture` -> `projects/<slug>/architecture/`
- `decision` -> `projects/<slug>/decisions/`
- `note` -> `projects/<slug>/notes/`
- `open-question` -> `projects/<slug>/open-questions/`
- `todo` -> `projects/<slug>/todo/`

## 14. Conflict Resolution Flow

`kiroku conflict list` shows conflicted files.

Implementation:

- Run `git status --porcelain`.
- Parse unmerged status codes.
- Show conflicted files.
- Group by project when the path is under `projects/<project-slug>/`.

`kiroku conflict resolve` guides human-in-the-loop resolution.

Flow:

1. List conflicted files.
2. For each file, show local version, remote version, and base version when available.
3. Offer actions: accept local, accept remote, edit manually, generate AI suggestion, abort.
4. If AI suggestion is requested, generate a merge suggestion from local/base/remote file content only.
5. Show the suggested merged content.
6. Ask the user to accept or edit.
7. Write resolved content only after confirmation.
8. Run `git add <resolved-files>`.
9. Continue rebase if a rebase is in progress.
10. Push after successful resolution and explicit confirmation.

AI conflict suggestions are advisory only. KirokuForge must not auto-resolve semantic conflicts.

## 15. Java Package And Module Architecture

Recommended Maven structure:

```text
kirokuforge/
├── pom.xml
├── README.md
├── LICENSE
├── docs/
├── kirokuforge-cli/
├── kirokuforge-core/
├── kirokuforge-agent/
├── kirokuforge-ai/
├── kirokuforge-git/
├── kirokuforge-knowledge/
├── kirokuforge-persistence/
└── kirokuforge-terminal/
```

Module responsibilities:

- `kirokuforge-cli`: Picocli entrypoint, command definitions, exit codes, command wiring.
- `kirokuforge-terminal`: JLine prompts, interactive chat, interactive review, interactive conflict resolution, colored terminal output.
- `kirokuforge-core`: use cases, business rules, project workflow, init workflow, save workflow, sync workflow, conflict workflow.
- `kirokuforge-agent`: Knowledge Processing Agent, signal extractor, classifier, artifact router, Markdown generator, validator, commit planner, prompt templates, structured output schemas.
- `kirokuforge-ai`: LLM provider abstraction, Codex CLI provider, OpenAI API provider, Ollama provider, model registry, auth status checking.
- `kirokuforge-git`: Git command executor, repository service, remote checker, sync service, status parser, diff service, conflict detector.
- `kirokuforge-knowledge`: knowledge tree service, Markdown reader/writer, frontmatter parser, template service, project structure service.
- `kirokuforge-persistence`: SQLite connection, Flyway migrations, settings repository, project repository, session repository, summary candidate repository, provider config repository.

Suggested base packages:

```text
dev.kirokuforge.cli
dev.kirokuforge.core
dev.kirokuforge.agent
dev.kirokuforge.ai
dev.kirokuforge.git
dev.kirokuforge.knowledge
dev.kirokuforge.persistence
dev.kirokuforge.terminal
```

## 16. Key Classes And Interfaces

Use cases:

```java
public final class InitKirokuForgeUseCase {}
public final class RepositoryStatusUseCase {}
public final class SyncRepositoryUseCase {}
public final class CreateProjectUseCase {}
public final class ListProjectsUseCase {}
public final class StartChatUseCase {}
public final class SaveSessionUseCase {}
public final class ShowDiffUseCase {}
public final class ListConflictsUseCase {}
public final class ResolveConflictsUseCase {}
public final class ConfigureAuthUseCase {}
public final class ListModelsUseCase {}
public final class UseModelUseCase {}
```

Git interface:

```java
public interface GitService {
    RemoteCheckResult checkRemote(String remoteUrl);
    void cloneRepository(String remoteUrl, Path localPath);
    void fetch(Path repoPath);
    void pullRebase(Path repoPath, String branch);
    GitStatus status(Path repoPath);
    GitDiff diff(Path repoPath);
    void add(Path repoPath, List<Path> files);
    void commit(Path repoPath, String message);
    void push(Path repoPath, String branch);
}
```

Knowledge Processing Agent interface:

```java
public interface KnowledgeProcessingAgent {
    SummaryCandidate process(
        SessionContext sessionContext,
        ProjectContext projectContext,
        KnowledgeBaseContext knowledgeBaseContext
    );
}
```

Agent component interfaces:

```java
public interface SignalExtractor {
    List<KnowledgeSignal> extract(SessionContext sessionContext);
}

public interface ArtifactRouter {
    List<ArtifactRoute> route(
        List<KnowledgeSignal> signals,
        ProjectContext projectContext,
        KnowledgeBaseContext knowledgeBaseContext
    );
}

public interface ArtifactGenerator {
    List<ArtifactCandidate> generate(
        List<KnowledgeSignal> signals,
        List<ArtifactRoute> routes
    );
}

public interface ArtifactValidator {
    ValidationResult validate(ArtifactCandidate artifact);
}

public interface CommitPlanner {
    CommitPlan plan(SummaryCandidate candidate);
}
```

Supporting classes:

```java
public final class GitCommandExecutor {}
public final class RemoteRepositoryChecker {}
public final class GitSyncService {}
public final class GitStatusParser {}
public final class GitConflictDetector {}
public final class KnowledgeTreeService {}
public final class MarkdownArtifactReader {}
public final class MarkdownArtifactWriter {}
public final class FrontmatterParser {}
public final class TemplateService {}
public final class ProjectStructureService {}
public final class SecretRedactor {}
public final class RawConversationLeakDetector {}
public final class ArtifactPathPolicy {}
```

## 17. SQLite Schema

Initial Flyway migration:

```sql
create table settings (
  key text primary key,
  value text not null,
  updated_at text not null
);

create table knowledge_repositories (
  id text primary key,
  local_path text not null,
  remote_url text,
  default_branch text not null,
  mode text not null,
  created_at text not null
);

create table projects (
  id text primary key,
  name text not null,
  slug text not null unique,
  description text,
  local_path text not null,
  created_at text not null
);

create table chat_sessions (
  id text primary key,
  project_id text not null,
  started_at text not null,
  ended_at text,
  status text not null,
  foreign key (project_id) references projects(id)
);

create table chat_messages (
  id text primary key,
  session_id text not null,
  role text not null,
  content text not null,
  created_at text not null,
  foreign key (session_id) references chat_sessions(id)
);

create table summary_candidates (
  id text primary key,
  project_id text not null,
  session_id text not null,
  commit_message text,
  warnings_json text not null,
  requires_review integer not null,
  status text not null,
  created_at text not null,
  foreign key (project_id) references projects(id),
  foreign key (session_id) references chat_sessions(id)
);

create table artifact_candidates (
  id text primary key,
  summary_candidate_id text not null,
  type text not null,
  target_path text not null,
  title text not null,
  markdown_content text not null,
  confidence real not null,
  operation text not null,
  status text not null,
  foreign key (summary_candidate_id) references summary_candidates(id)
);

create table provider_configs (
  provider_id text primary key,
  config_json text not null,
  auth_status text not null,
  updated_at text not null
);

create table model_preferences (
  id text primary key,
  provider_id text not null,
  model_id text not null,
  is_default integer not null
);

create table merge_conflicts (
  id text primary key,
  project_id text,
  file_path text not null,
  local_version text,
  remote_version text,
  base_version text,
  ai_suggestion text,
  status text not null,
  created_at text not null,
  foreign key (project_id) references projects(id)
);
```

Indexes:

```sql
create index idx_chat_sessions_project_id on chat_sessions(project_id);
create index idx_chat_messages_session_id on chat_messages(session_id);
create index idx_summary_candidates_session_id on summary_candidates(session_id);
create index idx_artifact_candidates_summary_id on artifact_candidates(summary_candidate_id);
create index idx_merge_conflicts_status on merge_conflicts(status);
```

## 18. Error Handling

All command errors should be mapped at the CLI boundary to stable exit codes.

Examples:

```text
Repository not found or inaccessible.
Working tree is dirty. Commit, stash, or discard unrelated changes before continuing.
Sync conflict detected. Run: kiroku conflict resolve
No authenticated provider is configured. Run: kiroku auth login
Artifact target path escapes the project knowledge directory.
Raw conversation detected in generated artifact. Regenerate or edit before saving.
```

Exception categories:

- `InvalidInputException` -> exit code `2`
- `GitNotConfiguredException` -> exit code `3`
- `DirtyRepositoryException` -> exit code `4`
- `SyncConflictException` -> exit code `5`
- `AiProviderException` -> exit code `6`
- `UserAbortedException` -> exit code `7`
- `AuthenticationException` -> exit code `8`
- `RepositoryInaccessibleException` -> exit code `9`

Error messages should be direct and actionable. They should not expose secrets or provider credentials.

## 19. Testing Strategy

Unit tests:

- Slug generation.
- Path containment.
- Artifact validation.
- Required frontmatter validation.
- Required Markdown section validation.
- Raw conversation phrase rejection.
- Secret redaction.
- Artifact routing.
- Commit message planning.
- Git command construction.
- Git status parsing.
- Manifest parsing.

Integration tests:

- Temporary local Git repositories.
- Remote exists.
- Remote unreachable.
- Clone.
- Initialize empty repository.
- Pull before write.
- Commit.
- Push.
- Conflict detection.
- Conflict resolution.
- Local-only initialization.

AI tests:

- Mock `LlmProvider`.
- Deterministic `SummaryCandidate` generation.
- Snapshot test generated Markdown.
- Verify secret redaction before review.
- Verify raw conversation rejection.
- Provider auth status tests.

CLI tests:

- Picocli command parsing.
- Exit code mapping.
- Non-interactive failure paths.
- JLine prompt flows through a test terminal abstraction.

## 20. MVP Implementation Roadmap

Phase 1: Foundation

- Create Maven multi-module project.
- Add Picocli entrypoint.
- Add config path resolution.
- Add SQLite and Flyway setup.
- Add Git command executor.
- Add exit code mapping.

Phase 2: Repository And Project Flows

- Implement `kiroku init`.
- Implement remote/local repository setup.
- Generate manifest and templates.
- Implement `kiroku repo status`.
- Implement `kiroku sync`.
- Implement `kiroku project create`.
- Implement `kiroku project list`.

Phase 3: Knowledge Artifacts

- Add Markdown templates.
- Add frontmatter parser.
- Add artifact writer.
- Add path validation.
- Add secret redaction.
- Add raw conversation leak detector.

Phase 4: AI Provider MVP

- Implement Ollama provider.
- Implement Codex CLI provider wrapper.
- Add auth config commands.
- Add model listing.
- Add default model selection.

Phase 5: Chat And Save

- Implement JLine chat session.
- Add slash commands.
- Add local session persistence.
- Implement Knowledge Processing Agent.
- Add review/edit/discard flow.
- Add diff, commit, and push flow.

Phase 6: Conflicts And Hardening

- Add conflict detection.
- Implement `kiroku conflict list`.
- Implement `kiroku conflict resolve`.
- Add integration tests with temporary Git repositories.
- Add packaging and release artifacts.

Recommended first open-source cut:

- Fully working local-only mode.
- Remote Git mode using plain Git.
- Project creation.
- Ollama-backed Knowledge Processing Agent.
- Codex CLI provider adapter.
- Review-before-write save flow.
- Commit and push.
- Conflict detection with guided manual resolution.
