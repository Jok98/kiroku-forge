# KirokuForge MVP Technical Design

## 1. Product Definition

KirokuForge is a local-first, Git-native, developer-first CLI that turns AI-assisted work sessions into structured, reviewed, versioned Markdown project knowledge.

The CLI binary is:

```bash
kiroku
```

Macro project repositories use this naming convention:

```text
KirokuFM-<macro-project-slug>
```

`KirokuFM` means `KirokuForgeMemory`.

A macro project is a high-level knowledge container that can contain multiple projects. A project is a specific codebase, app, or technical initiative inside a macro project. Example: macro project `work` can contain projects `sealforge`, `taskete`, and `kirokuforge`.

Each macro project is its own local Git repository. The published source of truth is the macro project Git repository containing reviewed Markdown artifacts. Raw conversations may exist only as temporary local drafts outside the Git repository and must never be committed or pushed.

The core product flow is:

```text
User starts a project session
-> user works with AI
-> user runs /save or kiroku save
-> Knowledge Processing Agent extracts useful knowledge
-> KirokuForge proposes Markdown artifacts
-> user reviews/edits them
-> KirokuForge pulls latest main when a remote is configured
-> KirokuForge writes files
-> KirokuForge shows diff
-> user confirms
-> KirokuForge commits
-> KirokuForge pushes when a remote is configured
```

The architecture distinguishes two AI roles:

- Chat Assistant: helps during the interactive session with reasoning, writing, debugging, design, and analysis.
- Knowledge Processing Agent: post-processes the session into durable project knowledge.

The Knowledge Processing Agent is intentionally separate from the Chat Assistant. It may propose artifacts and commit messages, but it must not commit, push, silently overwrite files, save raw conversation into Git, invent decisions, or resolve semantic conflicts.

## 2. Business Rules

- KirokuForge must not require a SaaS backend.
- Git is the source of truth for published macro project knowledge.
- Each macro project must be stored in its own Git repository named `KirokuFM-<macro-project-slug>`.
- `kiroku macro create` must always create the local Git repository first, even if no remote is configured.
- After local macro project creation, KirokuForge must show the exact remote repository name to create, for example `KirokuFM-work`.
- The default macro project path is `~/KirokuForge/KirokuFM-<macro-project-slug>/`.
- The default macro project path may be overridden by config or `--path`.
- Raw conversations must never be committed or pushed to Git.
- Raw chat drafts may be saved temporarily only in local application storage outside the macro project Git repository.
- Summary generation from a raw draft must happen only after an explicit user command.
- Only reviewed, structured Markdown artifacts may be written to the macro project repository.
- Every generated artifact requires explicit user review before writing.
- Every commit requires explicit user confirmation.
- Every remote write must be preceded by `git pull --rebase origin main` when a remote is configured.
- Git remotes are provider-agnostic and must work with GitHub, GitLab, Gitea, Bitbucket, and any remote supported by Git.
- KirokuForge must use the user's local Git, SSH agent, and credential helpers.
- KirokuForge must use pure Git CLI operations as the primary Git implementation.
- KirokuForge must not depend on GitHub CLI.
- If `git ls-remote <remote-url>` fails, KirokuForge must print exactly: `Repository not found or inaccessible.`
- KirokuForge must not infer whether a failed remote check is caused by a missing repository, missing permissions, broken SSH, or network failure.
- If the remote is unreachable, the user must manually create a repository with the exact suggested `KirokuFM-<macro-project-slug>` name on their Git provider.
- After user confirmation, KirokuForge must re-run `git ls-remote`.
- If a cloned or local repository is empty or missing `kirokuforge.yml`, KirokuForge must ask whether to initialize the repository structure.
- KirokuForge must never silently overwrite remote content.
- In the MVP, Git conflicts must be detected and the workflow must stop with manual resolution instructions.
- KirokuForge must not provide `kiroku conflict resolve` in the MVP.
- Secrets, API keys, tokens, and private credentials must be redacted before artifact review.
- Artifact target paths must stay under `projects/<project-slug>/`.
- Generated artifacts must be integrated into the project's single Markdown files, not written as separate per-artifact files.
- No file write is allowed without user approval.
- No commit is allowed without user approval.
- No push is allowed while unresolved conflicts exist.

## 3. Command List And CLI UX

The first working version provides these commands:

```bash
kiroku init
kiroku macro create <macro-project-name> [--path <path>]
kiroku macro clone <remote-url> [--path <path>]
kiroku macro list
kiroku macro use <macro-project-name>
kiroku macro remote add <macro-project-name> <remote-url>
kiroku repo status [--macro <macro-project-name>]
kiroku sync [--macro <macro-project-name>]
kiroku project create <project-name> [--macro <macro-project-name>]
kiroku project list [--macro <macro-project-name>]
kiroku chat <project-name> [--macro <macro-project-name>]
kiroku save <project-name> [--macro <macro-project-name>]
kiroku diff [project-name] [--macro <macro-project-name>]
kiroku conflict list
kiroku draft list
kiroku draft delete <draft-id>
kiroku auth login
kiroku auth list
kiroku models list
kiroku models use <provider:model>
```

Interactive flows should use JLine. Prompts must make destructive or publishing actions explicit and default to safe answers.

Examples:

```text
Integrate these 3 artifacts into the project Markdown files? [y/N]
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

Each macro project is a Git repository. The repository name uses `KirokuFM-<macro-project-slug>`.

```text
KirokuFM-work/
├── README.md
├── kirokuforge.yml
├── projects/
│   ├── sealforge/
│   │   ├── overview.md
│   │   ├── architecture.md
│   │   ├── decisions.md
│   │   ├── notes.md
│   │   ├── open-questions.md
│   │   └── todo.md
│   └── taskete/
│       ├── overview.md
│       ├── architecture.md
│       ├── decisions.md
│       ├── notes.md
│       ├── open-questions.md
│       └── todo.md
└── templates/
    ├── architecture.md
    ├── decisions.md
    ├── notes.md
    ├── open-questions.md
    ├── todo.md
    └── overview.md
```

Repository manifest:

```yaml
version: 1

repository:
  type: kirokuforge-macro-project
  name: KirokuFM-work
  macro_project: work
  remote_name: KirokuFM-work
  default_branch: main

layout:
  projects_dir: projects
  templates_dir: templates

rules:
  raw_conversations_commit_allowed: false
  temporary_raw_drafts_allowed: true
  raw_drafts_storage: local_app_data_only
  summary_generation_requires_user_command: true
  pull_before_write: true
  require_user_review_before_commit: true
  conflict_resolution: detect_and_stop_mvp
```

## 5. Git Workflow

KirokuForge uses Git CLI through `ProcessBuilder`.

Required Git commands:

```bash
git init
git ls-remote <remote-url>
git clone <remote-url> <local-path>
git remote add origin <remote-url>
git fetch origin
git pull --rebase origin main
git status --porcelain
git diff
git add <files>
git commit -m "<message>"
git push origin main
```

Remote mode rules:

- `kiroku macro create` creates the local repository first.
- `kiroku macro remote add` checks remote reachability and then configures `origin`.
- Check remote reachability before clone.
- Clone only after `git ls-remote <remote-url>` succeeds.
- Run `git fetch origin` and `git pull --rebase origin main` before every write.
- Stop on conflicts and print manual resolution instructions.
- Do not write generated files into a conflicted working tree.
- Do not commit if validation fails.
- Do not push until the user confirms.

Local-only mode rules:

- Initialize a local Git repository.
- Initialize the same KirokuForge repository structure.
- Use the same validation, review, diff, and commit flow.
- Skip remote reachability, fetch, pull, and push.

## 6. Init And Macro Project Workflow

`kiroku init` initializes local KirokuForge configuration and may guide the user into creating or cloning a macro project.

Local config paths on Linux:

```text
~/.config/kirokuforge/config.yml
~/.local/share/kirokuforge/kirokuforge.db
~/.local/share/kirokuforge/auth.json
~/.local/share/kirokuforge/drafts/
~/.cache/kirokuforge/
~/KirokuForge/KirokuFM-<macro-project-slug>/
```

`kiroku macro create <macro-project-name> [--path <path>]`:

1. Create local config directory if missing.
2. Convert the macro project name into a slug, for example `Work Projects` -> `work-projects`.
3. Resolve the local path from `--path`, config, or `~/KirokuForge/KirokuFM-<slug>/`.
4. Create the local directory.
5. Run `git init`.
6. Create `README.md`, `kirokuforge.yml`, `projects/`, and `templates/`.
7. Commit the initial structure locally.
8. Print the exact remote repository name the user should create, for example `KirokuFM-work-projects`.
9. Do not require or configure a remote.

`kiroku macro remote add <macro-project-name> <remote-url>`:

1. Resolve the macro project.
2. Run `git ls-remote <remote-url>`.
3. If unreachable, print `Repository not found or inaccessible.`
4. Tell the user to manually create a remote repository with the exact `KirokuFM-<slug>` name.
5. After confirmation, retry `git ls-remote <remote-url>`.
6. Run `git remote add origin <remote-url>`.
7. Push the current branch to `origin main`.

`kiroku macro list` lists locally registered macro projects.

`kiroku macro use <macro-project-name>` sets the active macro project.

`kiroku macro clone <remote-url> [--path <path>]`:

1. Run `git ls-remote <remote-url>`.
2. If unreachable, print `Repository not found or inaccessible.`
3. Clone with `git clone <remote-url> <local-path>`.
4. Validate that `kirokuforge.yml` exists and has repository type `kirokuforge-macro-project`.
5. Register the macro project locally.

## 7. Project Workflow

`kiroku project create <project-name>` creates a project knowledge area inside the active macro project repository. A `--macro <macro-project-name>` option may override the active macro project.

Slug rules:

- Lowercase.
- Replace spaces and separators with `-`, for example `Seal Forge` -> `seal-forge`.
- Remove unsafe path characters.
- Reject empty slugs.
- Reject `.` and `..`.
- Reject path traversal.

Generated structure:

```text
projects/<project-slug>/
├── overview.md
├── architecture.md
├── decisions.md
├── notes.md
├── open-questions.md
└── todo.md
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

`kiroku project list` lists available projects under `projects/` for the active macro project, or for the macro project selected with `--macro`.

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

The session may be stored as a temporary local raw draft for resumability, but session data must not be written into the macro project repository. Drafts are stored under local application data, for example `~/.local/share/kirokuforge/drafts/`, and are managed by:

```bash
kiroku draft list
kiroku draft delete <draft-id>
```

The Chat Assistant helps the user work. It does not decide what durable knowledge is saved. Durable knowledge is produced only by the Knowledge Processing Agent during the explicit `kiroku save` or `/save` command.

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
11. Integrate approved artifacts into the project's single Markdown files.
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
- Route content to the target project Markdown file.
- Generate Markdown.
- Propose commit messages.
- Validate that raw conversation is not being saved.
- Prepare a `SummaryCandidate` for user review.

The agent must not:

- Commit directly.
- Push directly.
- Silently overwrite files.
- Save raw conversation into Git.
- Invent decisions.
- Resolve semantic conflicts.

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
Route each artifact to the correct project Markdown file.
Output must be structured and machine-parseable.
```

Recommended structured output:

```json
{
  "artifacts": [
    {
      "type": "decision",
      "targetPath": "projects/example-project/decisions.md",
      "title": "Use Git as the source of truth for knowledge",
      "markdownContent": "...",
      "confidence": 0.91,
      "operation": "APPEND_SECTION"
    }
  ],
  "commitMessage": "docs(example-project): record Git-backed knowledge decisions",
  "warnings": [],
  "requiresReview": true
}
```

Validation rules:

- Target path must be under `projects/<project-slug>/`.
- Target path must be one of the standard project Markdown files.
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

- `MacroProject`
- `Project`
- `KnowledgeRepository`
- `ChatSession`
- `RawDraft`
- `KnowledgeSignal`
- `SummaryCandidate`
- `ArtifactCandidate`
- `MergeConflict`

Raw messages may be persisted locally as temporary drafts for resumability, but must be marked as local-only and excluded from Git.

Domain entity summaries:

```text
MacroProject
- id
- name
- slug
- repositoryName
- localPath
- active
- createdAt

Project
- id
- macroProjectId
- name
- slug
- description
- localPath
- createdAt

KnowledgeRepository
- macroProjectId
- name
- slug
- prefix
- localPath
- remoteUrl
- defaultBranch
- mode: REMOTE or LOCAL_ONLY

ChatSession
- id
- macroProjectId
- projectId
- startedAt
- endedAt
- status
- transient messages or local-only session data

RawDraft
- id
- macroProjectId
- projectId
- sessionId
- localPath
- status
- createdAt
- expiresAt

KnowledgeSignal
- type
- content
- confidence
- rationale

SummaryCandidate
- id
- macroProjectId
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
- operation: APPEND_SECTION, UPDATE_SECTION

MergeConflict
- id
- macroProjectId
- projectId
- filePath
- localVersion
- remoteVersion
- baseVersion
- status
```

## 13. Markdown Templates

Default project file frontmatter:

```markdown
---
project: <project-slug>
type: <overview|architecture|decisions|notes|open-questions|todo>
status: draft
created_at: <yyyy-mm-dd>
updated_at: <yyyy-mm-dd>
tags:
  - <tag>
---

# <Project Title> - <File Purpose>
```

Default generated section format:

```markdown
## <yyyy-mm-dd> - <Title>

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
templates/architecture.md
templates/decisions.md
templates/notes.md
templates/open-questions.md
templates/todo.md
templates/overview.md
```

Project files:

```text
projects/<project-slug>/overview.md
projects/<project-slug>/architecture.md
projects/<project-slug>/decisions.md
projects/<project-slug>/notes.md
projects/<project-slug>/open-questions.md
projects/<project-slug>/todo.md
```

Artifacts are integrated into these project files as reviewed sections. KirokuForge should append or update clearly delimited sections inside the target file rather than creating one file per artifact.

Artifact type routing:

- `architecture` -> `projects/<slug>/architecture.md`
- `decision` -> `projects/<slug>/decisions.md`
- `note` -> `projects/<slug>/notes.md`
- `open-question` -> `projects/<slug>/open-questions.md`
- `todo` -> `projects/<slug>/todo.md`

## 14. Conflict Detection Flow

`kiroku conflict list` shows conflicted files.

Implementation:

- Run `git status --porcelain`.
- Parse unmerged status codes.
- Show conflicted files.
- Group by project when the path is under `projects/<project-slug>/`.

MVP behavior:

1. Detect conflicted files.
2. Stop the current workflow.
3. Print the conflicted file list.
4. Print manual Git resolution instructions.
5. Do not write files.
6. Do not generate AI merge suggestions.
7. Do not provide `kiroku conflict resolve` in the MVP.

Future versions may add AI-assisted conflict resolution, but it is explicitly out of MVP.

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
- `kirokuforge-terminal`: JLine prompts, interactive chat, interactive review, conflict detection instructions, colored terminal output.
- `kirokuforge-core`: use cases, business rules, macro project workflow, project workflow, init workflow, save workflow, sync workflow, conflict detection workflow.
- `kirokuforge-agent`: Knowledge Processing Agent, signal extractor, classifier, artifact router, Markdown generator, validator, commit planner, prompt templates, structured output schemas.
- `kirokuforge-ai`: LLM provider abstraction, Codex CLI provider, OpenAI API provider, Ollama provider, model registry, auth status checking.
- `kirokuforge-git`: Git command executor, repository service, remote checker, sync service, status parser, diff service, conflict detector.
- `kirokuforge-knowledge`: knowledge tree service, Markdown reader/writer, frontmatter parser, template service, project structure service.
- `kirokuforge-persistence`: SQLite connection, Flyway migrations, settings repository, macro project repository, project repository, draft repository, session repository, summary candidate repository, provider config repository.

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
public final class CreateMacroProjectUseCase {}
public final class ListMacroProjectsUseCase {}
public final class UseMacroProjectUseCase {}
public final class AddMacroProjectRemoteUseCase {}
public final class RepositoryStatusUseCase {}
public final class SyncRepositoryUseCase {}
public final class CreateProjectUseCase {}
public final class ListProjectsUseCase {}
public final class StartChatUseCase {}
public final class SaveSessionUseCase {}
public final class ShowDiffUseCase {}
public final class ListConflictsUseCase {}
public final class ListDraftsUseCase {}
public final class DeleteDraftUseCase {}
public final class ConfigureAuthUseCase {}
public final class ListModelsUseCase {}
public final class UseModelUseCase {}
```

Git interface:

```java
public interface GitService {
    void initRepository(Path localPath);
    RemoteCheckResult checkRemote(String remoteUrl);
    void cloneRepository(String remoteUrl, Path localPath);
    void addRemote(Path repoPath, String name, String remoteUrl);
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

create table macro_projects (
  id text primary key,
  name text not null,
  slug text not null unique,
  repository_name text not null unique,
  local_path text not null unique,
  active integer not null,
  created_at text not null
);

create table knowledge_repositories (
  id text primary key,
  macro_project_id text not null,
  name text not null,
  slug text not null,
  prefix text not null,
  local_path text not null,
  remote_url text,
  default_branch text not null,
  mode text not null,
  created_at text not null,
  foreign key (macro_project_id) references macro_projects(id)
);

create table projects (
  id text primary key,
  macro_project_id text not null,
  name text not null,
  slug text not null,
  description text,
  local_path text not null,
  created_at text not null,
  unique (macro_project_id, slug),
  foreign key (macro_project_id) references macro_projects(id)
);

create table chat_sessions (
  id text primary key,
  macro_project_id text not null,
  project_id text not null,
  started_at text not null,
  ended_at text,
  status text not null,
  foreign key (macro_project_id) references macro_projects(id),
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

create table raw_drafts (
  id text primary key,
  macro_project_id text not null,
  project_id text,
  session_id text,
  local_path text not null,
  status text not null,
  created_at text not null,
  expires_at text,
  foreign key (macro_project_id) references macro_projects(id),
  foreign key (project_id) references projects(id),
  foreign key (session_id) references chat_sessions(id)
);

create table summary_candidates (
  id text primary key,
  macro_project_id text not null,
  project_id text not null,
  session_id text not null,
  commit_message text,
  warnings_json text not null,
  requires_review integer not null,
  status text not null,
  created_at text not null,
  foreign key (macro_project_id) references macro_projects(id),
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
  macro_project_id text,
  project_id text,
  file_path text not null,
  local_version text,
  remote_version text,
  base_version text,
  status text not null,
  created_at text not null,
  foreign key (macro_project_id) references macro_projects(id),
  foreign key (project_id) references projects(id)
);
```

Indexes:

```sql
create index idx_projects_macro_project_id on projects(macro_project_id);
create index idx_chat_sessions_macro_project_id on chat_sessions(macro_project_id);
create index idx_chat_sessions_project_id on chat_sessions(project_id);
create index idx_chat_messages_session_id on chat_messages(session_id);
create index idx_raw_drafts_status on raw_drafts(status);
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
Sync conflict detected. Resolve the conflicts manually with Git, then rerun the command.
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
- Macro project slug and repository name generation.
- Draft metadata handling.

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
- Implement `kiroku macro create`.
- Implement `kiroku macro list`.
- Implement `kiroku macro use`.
- Implement `kiroku macro remote add`.
- Implement local-first macro project repository setup.
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
- Add temporary raw draft persistence outside Git.
- Implement `kiroku draft list`.
- Implement `kiroku draft delete`.
- Implement Knowledge Processing Agent.
- Add review/edit/discard flow.
- Add diff, commit, and push flow.

Phase 6: Conflicts And Hardening

- Add conflict detection.
- Implement `kiroku conflict list`.
- Add integration tests with temporary Git repositories.
- Add packaging and release artifacts.

Recommended first open-source cut:

- Fully working local-only mode.
- Remote Git mode using plain Git.
- Macro project repositories named `KirokuFM-<slug>`.
- Project creation.
- Ollama-backed Knowledge Processing Agent.
- Codex CLI provider adapter.
- Review-before-write save flow.
- Commit and push.
- Conflict detection with manual resolution instructions.

Post-MVP:

- Add `kiroku conflict resolve`.
- Add human-in-the-loop conflict resolution UX.
- Add optional AI-assisted merge suggestions.
