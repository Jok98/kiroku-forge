package dev.kirokuforge.core.macro;

import org.junit.jupiter.api.Test;

import java.nio.file.Path;

import static org.assertj.core.api.Assertions.assertThat;

class MacroProjectPlannerTest {

    private final MacroProjectPlanner planner =
            new MacroProjectPlanner(new MacroProjectSlugGenerator());

    @Test
    void plansRepositoryNameFromMacroProjectName() {
        MacroProjectPreview preview = planner.plan("Seal Forge", Path.of("/tmp/custom"));

        assertThat(preview.name()).isEqualTo("Seal Forge");
        assertThat(preview.slug()).isEqualTo("seal-forge");
        assertThat(preview.repositoryName()).isEqualTo("KirokuFM-seal-forge");
        assertThat(preview.localPath()).isEqualTo(Path.of("/tmp/custom"));
    }
}