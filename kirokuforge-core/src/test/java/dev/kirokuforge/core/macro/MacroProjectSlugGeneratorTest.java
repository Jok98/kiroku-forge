package dev.kirokuforge.core.macro;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class MacroProjectSlugGeneratorTest {

    private final MacroProjectSlugGenerator generator = new MacroProjectSlugGenerator();

    @Test
    void convertsNameToSlug() {
        assertThat(generator.generate("Seal Forge")).isEqualTo("seal-forge");
    }

    @Test
    void collapsesSeparators() {
        assertThat(generator.generate("Seal___Forge!!")).isEqualTo("seal-forge");
    }

    @Test
    void removesAccents() {
        assertThat(generator.generate("Caffè Déjà Vu")).isEqualTo("caffe-deja-vu");
    }

    @Test
    void rejectsBlankName() {
        assertThatThrownBy(() -> generator.generate("   "))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("blank");
    }
}