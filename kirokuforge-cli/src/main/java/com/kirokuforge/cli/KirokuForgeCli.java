package com.kirokuforge.cli;

import picocli.CommandLine;
import picocli.CommandLine.Command;

@Command(
        name="kiroku",
        mixinStandardHelpOptions = true,
        version="kiroku 0.1.0-SNAPSHOT",
        description = "Turn AI work sessions into versioned project knowledge."
)
public final class KirokuForgeCli implements Runnable {
    public static void main(String[] args) {
        int exitCode = new CommandLine(new KirokuForgeCli()).execute(args);
        System.exit(exitCode);
    }

    @Override
    public void run(){
        CommandLine.usage(this, System.out);
    }

}
