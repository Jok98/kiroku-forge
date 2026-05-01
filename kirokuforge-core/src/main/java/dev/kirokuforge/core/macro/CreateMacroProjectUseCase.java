package dev.kirokuforge.core.macro;

import dev.kirokuforge.git.GitRepositoryService;
import dev.kirokuforge.knowledge.MacroProjectStructureWriter;

public class CreateMacroProjectUseCase {
    private static final String INITIAL_COMMIT_MESSAGE = "chore: initialize KirokuForge macro project knowledge base";

    private final MacroProjectPlanner planner;
    private final MacroProjectStructureWriter structureWriter;
    private final GitRepositoryService gitRepositoryService;

    public CreateMacroProjectUseCase(
            MacroProjectPlanner planner,
            MacroProjectStructureWriter structureWriter,
            GitRepositoryService gitRepositoryService
    ) {
        this.planner = planner;
        this.structureWriter = structureWriter;
        this.gitRepositoryService = gitRepositoryService;
    }

    public MacroProjectPreview create(CreateMacroProjectRequest request) {
        MacroProjectPreview preview = planner.plan(request.name(), request.path());

        structureWriter.createBaseStructure(
                preview.localPath(),
                preview.name(),
                preview.slug(),
                preview.repositoryName()
        );

        gitRepositoryService.initializeRepository(preview.localPath());
        gitRepositoryService.addAll(preview.localPath());
        gitRepositoryService.commit(preview.localPath(), INITIAL_COMMIT_MESSAGE);

        return preview;
    }
}
