package dev.kirokuforge.git;

public class GitCommandException extends RuntimeException{

    public GitCommandException(String message){
        super(message);
    }

    public GitCommandException(String message, Throwable cause){
        super(message, cause);
    }
}
