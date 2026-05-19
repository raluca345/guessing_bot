from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from typing import Union

import discord

from data.song import Song


@dataclass(slots=True)
class SongGuessingRound:
    song: Song
    song_pool: list[Song]
    question: Union[str, discord.File]  # either lyrics (str) or cropped image (File)
    answer_buffer: BytesIO  # for seeking and sending
    jacket_key: str
    language: str  # needed for replay button wiring



