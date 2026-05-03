package dev.kirokuforge.core.macro;

import dev.kirokuforge.git.GitCommandExecutor;
import dev.kirokuforge.git.GitRepositoryService;
import dev.kirokuforge.knowledge.MacroProjectStructureWriter;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.nio.file.Files;
import java.nio.file.Path;

import static org.assertj.core.api.Assertions.assertThat;

class CreateMacroProjectUseCaseTest {

    @TempDir
    Path tempDir;

    @Test
    void createsMacroProjectRepositoryWithInitialCommit() throws Exception {
        Path repositoryPath = tempDir.resolve("KirokuFM-seal-forge");

        CreateMacroProjectUseCase useCase = new CreateMacroProjectUseCase(
                new MacroProjectPlanner(new MacroProjectSlugGenerator()),
                new MacroProjectStructureWriter(),
                new GitRepositoryService(new GitCommandExecutor()),
                new MacroProjectPathPolicy()
        );

        MacroProjectPreview preview = useCase.create(
                new CreateMacroProjectRequest("Seal Forge", repositoryPath)
        );

        assertThat(preview.name()).isEqualTo("Seal Forge");
        assertThat(preview.slug()).isEqualTo("seal-forge");
        assertThat(preview.repositoryName()).isEqualTo("KirokuFM-seal-forge");
        assertThat(preview.localPath()).isEqualTo(repositoryPath);

        assertThat(repositoryPath.resolve(".git")).isDirectory();
        assertThat(repositoryPath.resolve("README.md")).isRegularFile();
        assertThat(repositoryPath.resolve("kirokuforge.yml")).isRegularFile();
        assertThat(repositoryPath.resolve("projects")).isDirectory();
        assertThat(repositoryPath.resolve("templates")).isDirectory();

        assertThat(repositoryPath.resolve("templates/overview.md")).isRegularFile();
        assertThat(repositoryPath.resolve("templates/architecture.md")).isRegularFile();
        assertThat(repositoryPath.resolve("templates/decisions.md")).isRegularFile();
        assertThat(repositoryPath.resolve("templates/notes.md")).isRegularFile();
        assertThat(repositoryPath.resolve("templates/open-questions.md")).isRegularFile();
        assertThat(repositoryPath.resolve("templates/todo.md")).isRegularFile();

        //git branch --show-current
        assertThat(gitOutput(repositoryPath, "branch", "--show-current"))
                .isEqualTo("main");

        //git log --oneline --max-count=1
        assertThat(gitOutput(repositoryPath, "log", "--oneline", "--max-count=1"))
                .contains("chore: initialize KirokuForge macro project knowledge base");
    }

    private String gitOutput(Path workingDirectory, String... arguments) throws Exception {
        String[] command = new String[arguments.length + 1];
        command[0] = "git";
        System.arraycopy(arguments, 0, command, 1, arguments.length);

        Process process = new ProcessBuilder(command)
                .directory(workingDirectory.toFile())
                .redirectErrorStream(true)
                .start();

        String output = new String(process.getInputStream().readAllBytes()).trim();
        int exitCode = process.waitFor();

        if (exitCode != 0) {
            throw new IllegalStateException("Git command failed: " + String.join(" ", command) + "\n" + output);
        }

        return output;
    }
}