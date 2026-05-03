package dev.kirokuforge.cli;

import dev.kirokuforge.core.macro.*;
import dev.kirokuforge.git.GitCommandExecutor;
import dev.kirokuforge.git.GitRepositoryService;
import dev.kirokuforge.knowledge.MacroProjectStructureWriter;
import dev.kirokuforge.core.macro.MacroProjectPathPolicy;
import picocli.CommandLine;
import picocli.CommandLine.Command;
import picocli.CommandLine.Option;
import picocli.CommandLine.Parameters;

import java.nio.file.Path;
import java.util.concurrent.Callable;

@Command(
        name = "kiroku",
        mixinStandardHelpOptions = true,
        version = "kiroku 0.1.0-SNAPSHOT",
        description = "Turn AI work sessions into versioned project knowledge.",
        subcommands = {
                KirokuForgeCli.MacroCommand.class
        }
)
public final class KirokuForgeCli implements Runnable {

    public static void main(String[] args) {
        int exitCode = new CommandLine(new KirokuForgeCli()).execute(args);
        System.exit(exitCode);
    }

    @Override
    public void run() {
        CommandLine.usage(this, System.out);
    }


    @Command(
            name = "macro",
            description = "Manage macro project repositories.",
            subcommands = {
                    MacroCreateCommand.class
            }
    )
    static final class MacroCommand implements Runnable {
        @Override
        public void run() {
            CommandLine.usage(this, System.out);
        }
    }

    @Command(
            name = "create",
            description = "Create a local macro project repository."
    )
    static final class MacroCreateCommand implements Callable<Integer> {
        @Parameters(
                index = "0",
                paramLabel = "<macro-project-name>",
                description = "Macro project name, for example: Work."
        )
        private String name;

        @Option(
                names = "--path",
                paramLabel = "<path>",
                description = "Override the default local repository path."
        )
        private Path path;

        @Override
        public Integer call() {
            CreateMacroProjectUseCase useCase = new CreateMacroProjectUseCase(
                    new MacroProjectPlanner(new MacroProjectSlugGenerator()),
                    new MacroProjectStructureWriter(),
                    new GitRepositoryService(new GitCommandExecutor()),
                    new MacroProjectPathPolicy()
            );
            try {

                MacroProjectPreview preview = useCase.create(new CreateMacroProjectRequest(name, path));

                System.out.println("Macro project created at: ");
                System.out.println("  name: " + preview.name());
                System.out.println("  slug: " + preview.slug());
                System.out.println("  repository: " + preview.repositoryName());
                System.out.println("  local path: " + preview.localPath());
                System.out.println();
                System.out.println("Remote repository name to create:");
                System.out.println("  " + preview.repositoryName());

                return 0;
            } catch (MacroProjectCreationException e) {
                System.err.println("Error: " + e.getMessage());
                return 2;
            }

        }
    }
}
