from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class Character:
    character_id: int
    character_name: str
    character_last_name: str
    aliases: list[str]

    @classmethod
    def from_db_row(cls, row: dict) -> "Character":
        aliases = row.get("aliases", [])

        return cls(
            character_id=row["characterId"],
            character_name=row["characterName"],
            character_last_name=row["characterLastName"],
            aliases=aliases,
        )


    def display_name(self) -> str:
        """Get the full character name."""
        return f"{self.character_last_name} {self.character_name}"

    def matches(self, guess: str) -> bool:
        """Check if a guess matches this character's name or aliases."""
        guess_clean = guess.lower().strip("-")

        return (
            guess_clean == self.character_name.lower()
            or guess_clean == self.character_name.lower().strip("-")
            or guess in self.aliases
            or guess.strip("-") in self.aliases
        )

