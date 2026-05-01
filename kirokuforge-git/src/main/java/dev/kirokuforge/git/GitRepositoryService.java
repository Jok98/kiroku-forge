package dev.kirokuforge.git;

import java.nio.file.Path;

public class GitRepositoryService {

    private final GitCommandExecutor gitCommandExecutor;

    public GitRepositoryService(GitCommandExecutor gitCommandExecutor) {
        this.gitCommandExecutor = gitCommandExecutor;
    }

    public void initializeRepository(Path repositoryPath){
        gitCommandExecutor.run(repositoryPath, "init", "-b", "main");
    }

    public void addAll(Path repositoryPath){
        gitCommandExecutor.run(repositoryPath, "add", ".");
    }

    public void commit(Path repositoryPath, String message){
        gitCommandExecutor.run(repositoryPath, "commit", "-m", message);
    }
}
