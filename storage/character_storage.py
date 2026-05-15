import json


class CharacterStorage:

    def __init__(self) -> None:
        self.characters_data = []
        with open("storage/characters.json", "r") as f:
            self.characters_data = json.load(f)
