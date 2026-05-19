import json

from data.character import Character


class CharacterStorage:

    def __init__(self) -> None:
        self.characters_data = []
        self._character_dict = None
        with open("storage/characters.json", "r") as f:
            self.characters_data = json.load(f)

    def _build_character_lookup_dict(self):
        """Build O(1) lookup dict indexed by characterId."""
        if self._character_dict is None:
            self._character_dict = {
                c.get("characterId"): c for c in self.characters_data
            }
        return self._character_dict

    def get_by_id(self, character_id: int) -> Character | None:
        """Get character by ID with O(1) lookup."""
        lookup_dict = self._build_character_lookup_dict()
        character_dict = lookup_dict.get(character_id)
        return Character.from_db_row(character_dict) if character_dict else None
