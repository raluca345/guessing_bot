import pytest
from re import sub

from utility.constants import PATTERN


def sanitize_guess(raw_guess: str) -> str:
    """Reproduce the sanitization applied to user guesses in both cogs."""
    guessed = sub(pattern=PATTERN, string=raw_guess.strip().lower(), repl="")
    guessed = guessed.replace(" ", "")
    return guessed.strip()


def sanitize_aliases(aliases: list[str]) -> list[str]:
    """Reproduce the alias sanitization applied before comparison."""
    return [sub(pattern=PATTERN, repl="", string=s.lower()) for s in aliases]


def guess_matches(raw_guess: str, romaji_name: str, aliases: list[str]) -> bool:
    """Return True if the guess matches the song name or any alias."""
    guessed = sanitize_guess(raw_guess)
    clean_aliases = sanitize_aliases(aliases)
    return guessed in clean_aliases or guessed == romaji_name.lower()


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
