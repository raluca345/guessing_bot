from storage.base_storage import BaseStorage


class CardStorage(BaseStorage):

    def __init__(self) -> None:
        super().__init__(use_dictionary=True)
        self.card_data = []
        self.get_card_data()

    def get_card_data(self):
        query = "SELECT id, assetbundle_name, card_rarity_type, prefix, en_prefix, release_at, support_unit, character_id FROM cards"
        rows = self.execute_query(query)

        for row in rows:
            if not row or row == {}:
                continue
            self.card_data.append(row)
