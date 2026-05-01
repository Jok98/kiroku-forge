package dev.kirokuforge.core.macro;

import java.nio.file.Path;

public record MacroProjectPreview(
        String name,
        String slug,
        String repositoryName,
        Path localPath
){

}
