package dev.kirokuforge.cli;

import dev.kirokuforge.core.macro.*;
import dev.kirokuforge.git.GitCommandExecutor;
import dev.kirokuforge.git.GitRepositoryService;
import dev.kirokuforge.knowledge.MacroProjectStructureWriter;
import picocli.CommandLine;
import picocli.CommandLine.Command;
import picocli.CommandLine.Option;
import picocli.CommandLine.Parameters;

import java.nio.file.Path;
import java.util.concurrent.Callable;

@Command(
        name="kiroku",
        mixinStandardHelpOptions = true,
        version="kiroku 0.1.0-SNAPSHOT",
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
    public void run(){
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
        public void run(){
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
                    new GitRepositoryService(new GitCommandExecutor())
            );

            MacroProjectPreview preview = useCase.create(new CreateMacroProjectRequest(name, path));

            return 0;
        }

    }
}
