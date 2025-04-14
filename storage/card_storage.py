from utility.utility_functions import connect, logger


class CardStorage:

    card_data = []

    connection = connect()
    cursor = connection.cursor(dictionary=True)

    def __init__(self) -> None:
        self.card_data = []
        self.get_card_data()

    def get_card_data(self):

        query = "SELECT id, assetbundle_name, card_rarity_type, prefix, en_prefix, release_at, support_unit, character_id FROM cards"

        self.cursor.execute(query)
        rows = self.cursor.fetchall()

        for row in rows:
            #logger.info(row)
            if not row or row == {}:
                continue
            self.card_data.append(row)

# card_storage = CardStorage()
# logger.info(card_storage.card_data)