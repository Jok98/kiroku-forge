package dev.kirokuforge.core.macro;


import java.nio.file.Path;

public record CreateMacroProjectRequest(
        String name,
        Path path
) {
}
