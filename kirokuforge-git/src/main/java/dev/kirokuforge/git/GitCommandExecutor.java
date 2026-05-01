package dev.kirokuforge.git;

import java.io.IOException;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;

public class GitCommandExecutor {

    public void run(Path workingDirectory, String... arguments){

        List<String> command = new ArrayList<>();
        command.add("git");
        command.addAll(List.of(arguments));

        ProcessBuilder processBuilder = new ProcessBuilder(command);
        processBuilder.directory(workingDirectory.toFile());
        processBuilder.redirectErrorStream(true);

        try {
            Process process = processBuilder.start();
            String output = new String(process.getInputStream().readAllBytes());
            int exitCode = process.waitFor();

            if (exitCode != 0){
                throw new GitCommandException("Git command failed: " + String.join(" ", command) + "\n" + output);
            }
        }catch (IOException e){
            throw new GitCommandException("Unable to start Git command: " + String.join(" ", command), e);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new GitCommandException("Git command interrupted: " + String.join(" ", command), e);
        }
    }

}
