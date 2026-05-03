package dev.kirokuforge.core.macro;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.nio.file.Files;
import java.nio.file.Path;

import static org.assertj.core.api.Assertions.assertThatCode;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class MacroProjectPathPolicyTest {

    private final MacroProjectPathPolicy policy = new MacroProjectPathPolicy();

    @TempDir
    Path tempDir;

    @Test
    void allowsMissingPath() {
        Path target = tempDir.resolve("KirokuFM-work");

        assertThatCode(() -> policy.ensureCreatable(target))
                .doesNotThrowAnyException();
    }

    @Test
    void allowsEmptyDirectory() throws Exception {
        Path target = tempDir.resolve("KirokuFM-work");
        Files.createDirectory(target);

        assertThatCode(() -> policy.ensureCreatable(target))
                .doesNotThrowAnyException();
    }

    @Test
    void rejectsExistingFile() throws Exception {
        Path target = tempDir.resolve("KirokuFM-work");
        Files.writeString(target, "not a directory");

        assertThatThrownBy(() -> policy.ensureCreatable(target))
                .isInstanceOf(MacroProjectCreationException.class)
                .hasMessageContaining("not a directory");
    }

    @Test
    void rejectsNonEmptyDirectory() throws Exception {
        Path target = tempDir.resolve("KirokuFM-work");
        Files.createDirectory(target);
        Files.writeString(target.resolve("existing.txt"), "existing content");

        assertThatThrownBy(() -> policy.ensureCreatable(target))
                .isInstanceOf(MacroProjectCreationException.class)
                .hasMessageContaining("not empty");
    }
}