import pytest

from utility.utility_functions import guess_matches, sanitize_guess, sanitize_aliases


class TestQuestionMarkGuesses:
    """Guesses containing '?' should match aliases/names with or without '?'."""

    def test_guess_with_question_mark_matches_alias_with_question_mark(self):
        assert guess_matches("ready steady?", "Ready Steady", ["ready steady?"])

    def test_guess_with_question_mark_matches_alias_without_question_mark(self):
        assert guess_matches("ready steady?", "Ready Steady", ["ready steady"])

    def test_guess_without_question_mark_matches_alias_with_question_mark(self):
        assert guess_matches("ready steady", "Ready Steady", ["ready steady?"])

    def test_guess_with_question_mark_matches_romaji_name(self):
        assert guess_matches("ifx?", "ifx?", ["ifx"])


class TestExclamationMarkGuesses:
    """Guesses containing '!' should match aliases/names with or without '!'."""

    def test_guess_with_exclamation_mark_matches_alias_with_exclamation(self):
        assert guess_matches("bring it on!", "Bring It On!", ["bring it on!"])

    def test_guess_with_exclamation_mark_matches_alias_without_exclamation(self):
        assert guess_matches("bring it on!", "Bring It On!", ["bring it on"])

    def test_guess_without_exclamation_mark_matches_alias_with_exclamation(self):
        assert guess_matches("bring it on", "Bring It On!", ["bring it on!"])

    def test_guess_with_multiple_exclamation_marks(self):
        assert guess_matches("more more jump!!", "More More Jump", ["more more jump!!"])

    def test_guess_with_exclamation_mark_matches_romaji_name(self):
        assert guess_matches("idsmile!", "IDSMILE!", ["idsmile"])


class TestApostropheGuesses:
    """Guesses containing apostrophes should match aliases/names with or without them."""

    def test_guess_with_apostrophe_matches_alias_with_apostrophe(self):
        assert guess_matches("don't fight the music", "Don't Fight the Music", ["don't fight the music"])

    def test_guess_with_apostrophe_matches_alias_without_apostrophe(self):
        assert guess_matches("don't fight the music", "Don't Fight the Music", ["dont fight the music"])

    def test_guess_without_apostrophe_matches_alias_with_apostrophe(self):
        assert guess_matches("dont fight the music", "Don't Fight the Music", ["don't fight the music"])

    def test_guess_with_apostrophe_matches_romaji_name(self):
        assert guess_matches("it's", "It's", ["its"])

    def test_guess_with_right_single_quote(self):
        # Unicode right single quotation mark (')
        assert guess_matches("don\u2019t fight the music", "Don't Fight the Music", ["dont fight the music"])


class TestMixedSpecialCharacterGuesses:
    """Guesses mixing multiple special characters should still match."""

    def test_guess_with_question_and_exclamation(self):
        assert guess_matches("what's up?!", "What's Up", ["whats up"])

    def test_guess_with_apostrophe_and_exclamation(self):
        assert guess_matches("let's go!", "Let's Go!", ["let's go!"])

    def test_guess_with_all_special_chars(self):
        assert guess_matches("who's there?!", "Who's There", ["whos there"])

    def test_empty_guess_does_not_match(self):
        assert not guess_matches("", "Some Song", ["some song"])

    def test_completely_wrong_guess(self):
        assert not guess_matches("wrong song!", "Right Song", ["right song"])


class TestSpacingAndApostropheVariants:
    """Guesses with apostrophes, spaces in place of apostrophes, or neither should all match."""

    def test_guess_with_apostrophe_matches(self):
        assert guess_matches("you're", "You're", ["you're"])

    def test_guess_with_space_instead_of_apostrophe_matches(self):
        assert guess_matches("you re", "You're", ["you're"])

    def test_guess_without_apostrophe_or_space_matches(self):
        assert guess_matches("youre", "You're", ["you're"])

    def test_full_title_with_apostrophe(self):
        assert guess_matches("you're the one", "You're the One", ["you're the one"])

    def test_full_title_with_space_instead_of_apostrophe(self):
        assert guess_matches("you re the one", "You're the One", ["you're the one"])

    def test_full_title_without_apostrophe(self):
        assert guess_matches("youre the one", "You're the One", ["you're the one"])

    def test_extra_spaces_in_guess(self):
        assert guess_matches("  you're  the  one  ", "You're the One", ["you're the one"])

    def test_its_variants(self):
        assert guess_matches("it's showtime", "It's Showtime", ["it's showtime"])
        assert guess_matches("its showtime", "It's Showtime", ["it's showtime"])
        assert guess_matches("it s showtime", "It's Showtime", ["it's showtime"])


class TestTokenBasedShorthandMatching:
    """Test token-based matching for shorthand guesses (e.g., remembering only 2-3 words)."""

    def test_two_token_shorthand_matches_long_title(self):
        """'hoshi basho' should match 'Hoshi ni Ichiban Chikai Basho'."""
        assert guess_matches(
            "hoshi basho",
            "Hoshi ni Ichiban Chikai Basho",
            []
        )

    def test_two_token_shorthand_alternative_pair(self):
        """'ichiban chikai' should also match the same title."""
        assert guess_matches(
            "ichiban chikai",
            "Hoshi ni Ichiban Chikai Basho",
            []
        )

    def test_single_long_token_matches_title(self):
        """'resonance' (7+ chars) should match title containing it."""
        assert guess_matches(
            "resonance",
            "Kimi to Boku no Resonance",
            []
        )

    def test_filler_words_do_not_match_alone(self):
        """Filler words like 'ni' should not match via tokens (filtered out)."""
        assert not guess_matches(
            "ni",
            "Hoshi ni Ichiban Chikai Basho",
            []
        )

    def test_token_match_rejects_wrong_words(self):
        """'hoshi wrong' should not match if 'wrong' is not in title."""
        assert not guess_matches(
            "hoshi wrong",
            "Hoshi ni Ichiban Chikai Basho",
            []
        )

    def test_token_match_ignores_filler_words(self):
        """Filler words like 'ni' should not count toward meaningful tokens."""
        # 'ichiban chikai' has 2 meaningful tokens, 'ichiban chikai ni' still has 2
        assert guess_matches(
            "ichiban chikai ni",
            "Hoshi ni Ichiban Chikai Basho",
            []
        )

    def test_token_match_with_punctuation_preserved(self):
        """Token matching should still handle punctuation correctly."""
        assert guess_matches(
            "ready steady?",
            "Ready Steady",
            []
        )

    def test_token_match_against_alias_not_just_title(self):
        """Token matching should work against aliases too."""
        assert guess_matches(
            "we resonating",
            "Kimi to Boku no Resonance",
            ["we are resonating"]
        )

    def test_token_match_case_insensitive(self):
        """Token matching should be case insensitive."""
        assert guess_matches(
            "HOSHI BASHO",
            "hoshi ni ichiban chikai basho",
            []
        )

    def test_token_match_with_extra_spaces(self):
        """Extra spaces should not break token matching."""
        assert guess_matches(
            "  hoshi   basho  ",
            "Hoshi ni Ichiban Chikai Basho",
            []
        )


class TestSemanticAliasMatching:
    """Test matching against semantic/paraphrase aliases (meaning-based guesses)."""

    def test_semantic_alias_exact_match(self):
        """Exact match against a semantic alias."""
        assert guess_matches(
            "we are resonating",
            "Kimi to Boku no Resonance",
            ["we are resonating"]
        )

    def test_semantic_alias_with_punctuation_variation(self):
        """Semantic alias should handle punctuation variations."""
        assert guess_matches(
            "we are resonating!",
            "Kimi to Boku no Resonance",
            ["we are resonating"]
        )

    def test_semantic_alias_shorthand_from_paraphrase(self):
        """Shorthand from a semantic alias should work."""
        assert guess_matches(
            "we resonating",
            "Kimi to Boku no Resonance",
            ["we are resonating"]
        )

    def test_multiple_semantic_aliases(self):
        """Multiple semantic aliases should all be checked."""
        assert guess_matches(
            "our resonance",
            "Kimi to Boku no Resonance",
            ["we are resonating", "our resonance", "between you and me"]
        )

    def test_semantic_alias_shorthand_alternative_phrase(self):
        """Shorthand from alternative semantic phrase."""
        assert guess_matches(
            "between me",
            "Kimi to Boku no Resonance",
            ["we are resonating", "between you and me"]
        )

    def test_semantic_alias_does_not_match_unrelated_guess(self):
        """Unrelated guess should not match even with semantic aliases."""
        assert not guess_matches(
            "wrong guess",
            "Kimi to Boku no Resonance",
            ["we are resonating", "our resonance"]
        )


class TestExactMatchStillPrioritized:
    """Ensure exact matching is still the primary strategy and works correctly."""

    def test_exact_match_fastest_path(self):
        """Exact matches should take the fast path."""
        assert guess_matches("ready steady", "Ready Steady", ["ready steady"])
        assert guess_matches("ready steady?", "Ready Steady", ["ready steady"])

    def test_exact_match_against_title(self):
        """Exact match directly against the romaji title."""
        assert guess_matches(
            "Melt",
            "Melt",
            ["melting"]
        )

    def test_exact_match_no_false_positives(self):
        """Ensure exact matching doesn't have false positives."""
        assert not guess_matches(
            "melting",
            "Melt",
            []
        )


class TestComplexRealWorldExamples:
    """Test complex, realistic scenarios."""

    def test_gimme_gimme_shorthand(self):
        """'gimme' might match 'Gimme×Gimme'."""
        assert guess_matches(
            "gimme gimme",
            "Gimme×Gimme",
            []
        )

    def test_more_jump_shorthand(self):
        """'more jump' should match 'More! Jump! More!'."""
        assert guess_matches(
            "more jump",
            "More! Jump! More!",
            []
        )

    def test_world_end_shorthand(self):
        """'world end' should match 'World's End Dancehall'."""
        assert guess_matches(
            "world end",
            "World's End Dancehall",
            []
        )

    def test_complete_mismatch_fails(self):
        """Complete mismatch should always fail."""
        assert not guess_matches(
            "completely different song",
            "Some Song Title",
            ["some alias"]
        )
