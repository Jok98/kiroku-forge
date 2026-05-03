package dev.kirokuforge.core.macro;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.stream.Stream;

public final class MacroProjectPathPolicy {

    public void  ensureCreatable(Path path){
        if(Files.notExists(path)){
            return;
        }
        if(!Files.isDirectory(path)){
            throw new MacroProjectCreationException("Macro project path exists but is not a directory: " + path);
        }
        if (!isDirectoryEmpty(path)) {
            throw new MacroProjectCreationException("Macro project directory already exists and is not empty: " + path);
        }

    }

    private boolean isDirectoryEmpty(Path path){
        try (Stream<Path> entries = Files.list(path)){
            return entries.findAny().isEmpty();
        } catch (IOException e) {
            throw new MacroProjectCreationException("Unable to inspect macro project directory: " + path, e);
        }
    }
}
