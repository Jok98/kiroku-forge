package dev.kirokuforge.knowledge;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;

public class MacroProjectStructureWriter {

    /*
    create macro project structure :
        - README.md
        - kirokuforge.yml
        - projects/
        - templates/
     */
    public void createBaseStructure(Path repositoryPath, String macroProjectName, String macroProjectSlug, String repositoryName) {
        try {
            Files.createDirectories(repositoryPath);
            Files.createDirectories(repositoryPath.resolve("projects"));
            Files.createDirectories(repositoryPath.resolve("templates"));

            writeIfMissing(repositoryPath.resolve("README.md"), readme(repositoryName));
            writeIfMissing(repositoryPath.resolve("kirokuforge.yml"), manifest(macroProjectSlug, repositoryName));

            writeIfMissing(repositoryPath.resolve("templates").resolve("overview.md"), template("overview"));
            writeIfMissing(repositoryPath.resolve("templates").resolve("architecture.md"), template("architecture"));
            writeIfMissing(repositoryPath.resolve("templates").resolve("decisions.md"), template("decisions"));
            writeIfMissing(repositoryPath.resolve("templates").resolve("notes.md"), template("notes"));
            writeIfMissing(repositoryPath.resolve("templates").resolve("open-questions.md"), template("open-questions"));
            writeIfMissing(repositoryPath.resolve("templates").resolve("todo.md"), template("todo"));

        } catch (IOException e) {
            throw new IllegalStateException("Unable to create macro project structure at " + repositoryPath, e);
        }

    }

    private void writeIfMissing(Path path, String content) throws IOException {
        if (Files.notExists(path)) {
            Files.writeString(path, content);
        }
    }

    private String readme(String repositoryName) {
        return "# " + repositoryName + "\n\n" + "KirokuForge macro project knowledge repository.\n";
    }

    private String manifest(String macroProjectSlug, String repositoryName) {
        return """
                version: 1

                repository:
                    type: kirokuforge-macro-project
                    name: %s
                    macro_project: %s
                    remote_name: %s
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
        """.formatted(repositoryName, macroProjectSlug, repositoryName);
    }

    private String template(String type) {
        return """
                  ---
                  type: %s
                  status: draft
                  created_at:
                  updated_at:
                  tags: []
                  ---

                  # Title

                  ## Summary

                  ## Key Points

                  ## Decisions

                  ## Alternatives Considered

                  ## Open Questions

                  ## TODO

                  ## Related Files
                  """.formatted(type);
    }
}
