import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from cogs.twt_hub import TwtHub
from utility.constants import CGL_SERVER_ID, WEEK_ANNOUNCEMENT_CHANNEL

class AsyncIterator:
    def __init__(self, items):
        self.items = items

    def __aiter__(self):
        self._iter = iter(self.items)
        return self

    async def __anext__(self):
        try:
            return next(self._iter)
        except StopIteration:
            raise StopAsyncIteration

class TestTwtHub:
    @pytest.fixture
    def mock_bot(self):
        class MockBot:
            def __init__(self):
                self.get_guild = MagicMock(id=CGL_SERVER_ID)
                self.guilds = [MagicMock(id=CGL_SERVER_ID)]
                self.get_channel = MagicMock(id=WEEK_ANNOUNCEMENT_CHANNEL)
                self.character_names = ["Ichika", "Saki", "Honami", "Shiho", "Minori", "Haruka",
                                        "Airi", "Shizuku", "Kohane", "An", "Akito", "Toya",
                                        "Tsukasa", "Emu", "Nene", "Rui", "Kanade", "Mafuyu",
                                        "Ena", "Mizuki", "Miku", "Rin", "Len", "Luka", "Meiko",
                                        "Kaito"]

        return MockBot()

    @pytest.fixture
    def mock_character_storage(self):
        with patch("cogs.twt_hub.CharacterStorage") as MockCharacterStorage:
            mock_instance = MockCharacterStorage.return_value
            mock_instance.characters_data = [
                {"characterName": "Ichika"},
                {"characterName": "Saki"},
                {"characterName": "Honami"},
                {"characterName": "Shiho"},
                {"characterName": "Minori"},
                {"characterName": "Haruka"},
                {"characterName": "Airi"},
                {"characterName": "Shizuku"},
                {"characterName": "Kohane"},
                {"characterName": "An"},
                {"characterName": "Akito"},
                {"characterName": "Toya"},
                {"characterName": "Tsukasa"},
                {"characterName": "Emu"},
                {"characterName": "Nene"},
                {"characterName": "Rui"},
                {"characterName": "Kanade"},
                {"characterName": "Mafuyu"},
                {"characterName": "Ena"},
                {"characterName": "Mizuki"},
                {"characterName": "Miku"},
                {"characterName": "Rin"},
                {"characterName": "Len"},
                {"characterName": "Luka"},
                {"characterName": "Meiko"},
                {"characterName": "Kaito"}
            ]
            yield MockCharacterStorage

    @pytest.fixture
    def mock_twt_hub(self, mock_bot, mock_character_storage):
        twt_hub = TwtHub(mock_bot)
        twt_hub.client = AsyncMock()
        return twt_hub

    @pytest.fixture
    def mock_twt(self, mock_twt_hub, request):
        mock_twt_hub.client.get_users_tweets.return_value = MagicMock(
            data=[MagicMock(id='1234567890', text=request.param)]
        )

    @pytest.fixture
    def mock_channel(self):
        mock_channel = MagicMock()  # Not AsyncMock
        mock_channel.id = WEEK_ANNOUNCEMENT_CHANNEL
        mock_channel.name = "twt"
        mock_channel.permissions_for.return_value = MagicMock(
            send_messages=True,
            read_message_history=True
        )
        mock_channel.send = AsyncMock()

        def history(*args, **kwargs):
            return AsyncIterator([])

        mock_channel.history = history
        return mock_channel

    @pytest.fixture
    def mock_role(self):
        mock_role = MagicMock(mention="@Week Announcement Ping")
        mock_role.name = "Week Announcement Ping"
        return mock_role

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "mock_twt",
        [
            "The Summer Special - Week 142 of Card Guessing League will be held on 19/07 (Sat)"
            "\n\nStarter League: 8pm JST"
            "\nMain League 10pm JST"
            "\n\nIt's Toya Week! Let's get under the waves and start guessing!!"
        ],
        indirect=True
    )
    async def test_broadcast_tweets_to_channel_normal_week(self, mock_twt, mock_twt_hub, mock_channel, mock_role):

        mock_twt_hub.bot.get_channel.return_value = mock_channel
        mock_twt_hub.bot.get_guild.return_value.roles = [mock_role]
        mock_emoji = MagicMock(__str__=lambda self: ":ToyaStamp:")
        mock_emoji.name = "ToyaStamp"
        mock_twt_hub.bot.get_guild.return_value.emojis = [mock_emoji]

        print(f"Mock role mention: {mock_role.mention}")
        print(f"Mock channel: {mock_channel}")
        print(f"Mock emojis: {mock_twt_hub.bot.get_guild.return_value.emojis}")

        await mock_twt_hub.broadcast_tweets_to_channel()

        expected_message = (
            "# Week 142 has been announced!\n\n"
            "Reach deathmatch to earn a Toya stamp :ToyaStamp:!\n\n"
            "@prskcgl tweeted https://x.com/prskcgl/status/1234567890\n@Week Announcement Ping"
        )

        mock_channel.send.assert_called_once_with(expected_message)


    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "mock_twt",
        [
            "Week 141 of Card Guessing League will be held on 12/07 (Sat)"
            "\n\nStarter League: 8pm JST"
            "\nMain League 10pm JST"
            "\n\nIt's Akito and An Week! We're waiting for you!!"
        ],
        indirect=True
    )
    async def test_broadcast_tweets_to_channel_kizuna_week(self, mock_twt, mock_twt_hub, mock_channel, mock_role):
        mock_twt_hub.bot.get_channel.return_value = mock_channel
        mock_twt_hub.bot.get_guild.return_value.roles = [mock_role]
        mock_emoji1 = MagicMock(__str__=lambda self: ":AkitoStamp:")
        mock_emoji1.name = "AkitoStamp"
        mock_emoji2 = MagicMock(__str__=lambda self: ":AnStamp:")
        mock_emoji2.name = "AnStamp"
        mock_twt_hub.bot.get_guild.return_value.emojis = [mock_emoji1, mock_emoji2]

        await mock_twt_hub.broadcast_tweets_to_channel()

        expected_message = (
            "# Week 141 has been announced!\n\n"
            "Reach deathmatch to earn a An stamp :AnStamp: and a Akito stamp :AkitoStamp:!\n\n"
            "@prskcgl tweeted https://x.com/prskcgl/status/1234567890\n@Week Announcement Ping"
        )

        mock_channel.send.assert_called_once_with(expected_message)

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "mock_twt",
        [
            "Shuffle Unit Week - Week 138 of Card Guessing League will be held on 21/06 (Sat)"
            "\n\nMain League: 10pm JST"
            "\n\nThis round's focus are Luka, Akito, Rui and Ena!! Come enjoy the mysterious atmosphere!"
        ],
        indirect=True
    )
    async def test_broadcast_tweets_to_channel_shuffle_unit_week(self, mock_twt, mock_twt_hub, mock_channel, mock_role):
        mock_twt_hub.bot.get_channel.return_value = mock_channel
        mock_twt_hub.bot.get_guild.return_value.roles = [mock_role]
        mock_emoji1 = MagicMock(__str__=lambda self: ":LukaStamp:")
        mock_emoji1.name = "LukaStamp"
        mock_emoji2 = MagicMock(__str__=lambda self: ":AkitoStamp:")
        mock_emoji2.name = "AkitoStamp"
        mock_emoji3 = MagicMock(__str__=lambda self: ":RuiStamp:")
        mock_emoji3.name = "RuiStamp"
        mock_emoji4 = MagicMock(__str__=lambda self: ":EnaStamp:")
        mock_emoji4.name = "EnaStamp"
        mock_twt_hub.bot.get_guild.return_value.emojis = [mock_emoji1, mock_emoji2, mock_emoji3, mock_emoji4]

        await mock_twt_hub.broadcast_tweets_to_channel()

        expected_message = (
            "# Shuffle Unit Week 138 has been announced!\n\n"
            "Reach deathmatch to earn a shuffle unit stamp :AkitoStamp: "
            ":RuiStamp: :EnaStamp: :LukaStamp:!\n\n"
            "@prskcgl tweeted https://x.com/prskcgl/status/1234567890\n@Week Announcement Ping"
        )

        mock_channel.send.assert_called_once_with(expected_message)

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "mock_twt",
        [
            "MORE MORE JUMP! Unit Week - Week 99 of Card Guessing League will be held on 21/09 (Sat)"
            "\n\nMain League: 10pm JST"
            "\n\nGuess cards and deliver hope with us!!"
        ],
        indirect=True
    )
    async def test_broadcast_tweets_to_channel_unit_week(self, mock_twt, mock_twt_hub, mock_channel, mock_role):
        mock_twt_hub.bot.get_channel.return_value = mock_channel
        mock_twt_hub.bot.get_guild.return_value.roles = [mock_role]
        mock_emoji1 = MagicMock(__str__=lambda self: ":MinoriStamp:")
        mock_emoji1.name = "MinoriStamp"
        mock_emoji2 = MagicMock(__str__=lambda self: ":HarukaStamp:")
        mock_emoji2.name = "HarukaStamp"
        mock_emoji3 = MagicMock(__str__=lambda self: ":AiriStamp:")
        mock_emoji3.name = "AiriStamp"
        mock_emoji4 = MagicMock(__str__=lambda self: ":ShizukuStamp:")
        mock_emoji4.name = "ShizukuStamp"
        mock_twt_hub.bot.get_guild.return_value.emojis = [mock_emoji1, mock_emoji2, mock_emoji3, mock_emoji4]

        await mock_twt_hub.broadcast_tweets_to_channel()

        expected_message = (
            "# MORE MORE JUMP! Unit Week 99 has been announced!\n\n"
            "Reach deathmatch to earn a MORE MORE JUMP! stamp :MinoriStamp: "
            ":HarukaStamp: :AiriStamp: :ShizukuStamp:!\n\n"
            "@prskcgl tweeted https://x.com/prskcgl/status/1234567890\n@Week Announcement Ping"
        )

        mock_channel.send.assert_called_once_with(expected_message)

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "mock_twt",
        [
            "The 2nd Anniversary Special - Week 106 of Card Guessing League will be held on 09/11 (Sat)"
            "\n\nStarter League - 8pm JST"
            "\n2nd Anniv' News Program - 9:30pm JST"
            "\nMain League - 10:30pm JST"
            "\n\nStay tuned for exciting news and even more exciting games!! Happy 2nd Anniversary everyone!"
        ],
        indirect=True
    )
    async def test_broadcast_tweets_to_channel_everyone_week(self, mock_twt, mock_twt_hub, mock_channel, mock_role):
        mock_twt_hub.bot.get_channel.return_value = mock_channel
        mock_twt_hub.bot.get_guild.return_value.roles = [mock_role]

        await mock_twt_hub.broadcast_tweets_to_channel()

        expected_message = (
            "# Week 106 has been announced!\n\n"
            "Reach deathmatch to earn a stamp of your choice!\n\n"
            "@prskcgl tweeted https://x.com/prskcgl/status/1234567890\n@Week Announcement Ping"
        )

        mock_channel.send.assert_called_once_with(expected_message)