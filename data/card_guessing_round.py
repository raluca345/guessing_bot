from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO

from data.card import Card
from data.character import Character


@dataclass(slots=True)
class CardGuessingRound:
    card: Card
    character: Character
    question: bytes  # cropped card image
    answer_buffer: BytesIO  # resized full card image
    card_pool: list[Card]
    card_type: str  # "normal.png" or "after_training.png"

