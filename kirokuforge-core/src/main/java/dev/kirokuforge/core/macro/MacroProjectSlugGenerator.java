package dev.kirokuforge.core.macro;

import java.text.Normalizer;
import java.util.Locale;

public class MacroProjectSlugGenerator {

    public String generate(String name){
        if (name == null || name.isBlank()){
            throw new IllegalArgumentException("Macro project name cannot be null or blank");
        }

        //split characters and diacritical marks removing them
        String normalized =  Normalizer.normalize(name.trim(), Normalizer.Form.NFD)
                .replaceAll("\\p{M}", "");

        String slug = normalized
                .toLowerCase(Locale.ROOT) //stabilizes the slug and make it independent of the OS language
                .replaceAll("[^a-z0-9]+", "-") //if not alfanumeric it will be converted into -
                .replaceAll("-+", "-")// collapse multiple dashes
                .replaceAll("^-+|-+$", ""); // remove leading and trailing dashes

        if (slug.isBlank()){
            throw new IllegalArgumentException("Macro project name must contain at least one letter or digit.");
        }

        return slug;
    }
}
