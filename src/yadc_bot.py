from typing import List, Optional, Type

from discord import ApplicationCommand, SlashCommand, SlashCommandGroup
from discord.ext.commands import Bot

from .gdrive import TourneyDataClient
from . import settings




class YadcBot(Bot):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.__tournament_data_client: TourneyDataClient = None
        if settings.FEATURE_TOURNEYDATA_ENABLED:
            self.__tournament_data_client = TourneyDataClient(
                settings.GDRIVE_PROJECT_ID,
                settings.GDRIVE_PRIVATE_KEY_ID,
                settings.GDRIVE_PRIVATE_KEY,
                settings.GDRIVE_CLIENT_EMAIL,
                settings.GDRIVE_CLIENT_ID,
                settings.GDRIVE_SCOPES,
                settings.GDRIVE_FOLDER_ID,
                settings.GDRIVE_SERVICE_ACCOUNT_FILE,
                settings.GDRIVE_SETTINGS_FILE,
                settings.TOURNAMENT_DATA_START_DATE
            )

    @property
    def tournament_data_client(self) -> TourneyDataClient:
        return self.__tournament_data_client


    def get_application_command(
        self,
        name: str,
        guild_ids: Optional[List[int]] = None,
        type: Type[ApplicationCommand] = SlashCommand,
    ) -> Optional[ApplicationCommand]:
        """Get a :class:`.ApplicationCommand` from the internal list
        of commands.

        .. versionadded:: 2.0

        Parameters
        -----------
        name: :class:`str`
            The name of the command to get.
        guild_ids: List[:class:`int`]
            The guild ids associated to the command to get.
        type: Type[:class:`.ApplicationCommand`]
            The type of the command to get. Defaults to :class:`.SlashCommand`.

        Returns
        --------
        Optional[:class:`.ApplicationCommand`]
            The command that was requested. If not found, returns ``None``.
        """
        names = name.split()
        if not names:
            return None
        obj = next((cmd for cmd in self.application_commands if cmd.name == names[0]), None)
        if (type == SlashCommand and not isinstance(obj, SlashCommandGroup)) or isinstance(obj, type):
            return obj

        for name in names[1:]:
            try:
                obj = next((cmd for cmd in obj.subcommands if cmd.name == name), None)
            except AttributeError:
                return None

        if isinstance(obj, type) and (not guild_ids or set(obj.guild_ids) <= set(guild_ids)):
            return obj
        return None