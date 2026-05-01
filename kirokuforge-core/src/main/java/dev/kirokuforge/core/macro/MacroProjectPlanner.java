package dev.kirokuforge.core.macro;

import java.nio.file.Path;

public class MacroProjectPlanner {
    private static final String REPOSITORY_PREFIX = "KirokuFM";

    private final MacroProjectSlugGenerator slugGenerator;

    public MacroProjectPlanner(MacroProjectSlugGenerator slugGenerator) {
        this.slugGenerator = slugGenerator;
    }

    public MacroProjectPreview plan(String name, Path explicitPath){
        String slug = slugGenerator.generate(name);
        String repositoryName = REPOSITORY_PREFIX + "-" + slug;
        Path locclaPath = explicitPath!=null ? explicitPath : defaultLocalPath(repositoryName);

        return new MacroProjectPreview(
                name,
                slug,
                repositoryName,
                locclaPath
        );
    }

    private Path defaultLocalPath(String repositoryName){
        return Path.of(System.getProperty("user.home"),"KirokuForge", repositoryName);
    }
}
