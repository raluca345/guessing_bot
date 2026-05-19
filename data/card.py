from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class Card:
    id: int
    character_id: int
    card_rarity_type: str
    en_prefix: str
    prefix: str
    assetbundle_name: str

    @classmethod
    def from_db_row(cls, row: dict) -> "Card":
        return cls(
            id=row["id"],
            character_id=row["character_id"],
            card_rarity_type=row["card_rarity_type"],
            en_prefix=row.get("en_prefix", ""),
            prefix=row.get("prefix", ""),
            assetbundle_name=row.get("assetbundle_name", ""),
        )

    def display_name(self) -> str:
        """Get the card display name (English prefix if available, fallback to prefix)."""
        return self.en_prefix if self.en_prefix else self.prefix

    def card_key(self, card_type: str) -> str:
        """Get the R2 key for this card.
        
        Args:
            card_type: Either "normal.png" or "after_training.png"
        """
        return f"cards/card_{self.id}_{card_type}"

    def mask_key(self) -> str:
        """Get the R2 key for this card's mask (for 2-star cards)."""
        return f"masks/card_{self.id}_normal.npz"

