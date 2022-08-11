import os as _os
import calendar as _calendar

from discord.ext.commands import Bot as _Bot
from discord.ext.commands import command as _command
from discord.ext.commands import group as _command_group
from discord.ext.commands import Context as _Context
from discord.ext.commands import BucketType as _BucketType
from discord.ext.commands import cooldown as _cooldown

from . import BaseCog as _BaseCog
from ..pss_exception import Error as _Error
from ..pss_exception import MissingParameterError as _MissingParameterError
from ..pss_exception import NotFound as _NotFound
from .. import pss_fleet as _fleet
from ..gdrive import TourneyDataClient as _TourneyDataClient
from .. import pagination as _pagination
from .. import pss_top as _top
from .. import pss_tournament as _tourney
from .. import pss_user as _user
from .. import settings as _settings
from .. import server_settings as _server_settings
from .. import utils as _utils



class TournamentDataCog(_BaseCog, name='Fleet History'):
    """
    This extension offers commands to get information about fleets and players from past tournaments.
    """
    def __init__(self, bot: _Bot) -> None:
        super().__init__(bot)
        self.__tournament_data_client: _TourneyDataClient = _TourneyDataClient(
                _settings.GDRIVE_PROJECT_ID,
                _settings.GDRIVE_PRIVATE_KEY_ID,
                _settings.GDRIVE_PRIVATE_KEY,
                _settings.GDRIVE_CLIENT_EMAIL,
                _settings.GDRIVE_CLIENT_ID,
                _settings.GDRIVE_SCOPES,
                _settings.GDRIVE_FOLDER_ID,
                _settings.GDRIVE_SERVICE_ACCOUNT_FILE,
                _settings.GDRIVE_SETTINGS_FILE,
                _settings.TOURNAMENT_DATA_START_DATE
            )


    @property
    def tournament_data_client(self) -> _TourneyDataClient:
        return self.__tournament_data_client


    @_command_group(name='past', aliases=['history'], brief='Get historic data', invoke_without_command=True)
    @_cooldown(rate=_BaseCog.RATE, per=_BaseCog.COOLDOWN, type=_BucketType.user)
    async def past(self, ctx: _Context, month: str = None, year: str = None):
        """
        Get historic tournament data.

        Parameters:
        month: Optional. The month for which the data should be retrieved. Can be a number from 1 to 12, the month's name (January, ...) or the month's short name (Jan, ...)
        year:  Optional. The year for which the data should be retrieved. If the year is specified, the month has to be specified, too.

        If one or more of the date parameters are not specified, the bot will attempt to select the best matching month.

        You need to use one of the subcommands.
        """
        self._log_command_use(ctx)
        await ctx.send_help('past')


    @past.group(name='stars', brief='Get historic division stars', invoke_without_command=True)
    @_cooldown(rate=_BaseCog.RATE, per=_BaseCog.COOLDOWN, type=_BucketType.user)
    async def past_stars(self, ctx: _Context, month: str = None, year: str = None, *, division: str = None):
        """
        Get historic tournament division stars data.

        Parameters:
        month:    Optional. The month for which the data should be retrieved. Can be a number from 1 to 12, the month's name (January, ...) or the month's short name (Jan, ...)
        year:     Optional. The year for which the data should be retrieved. If the year is specified, the month has to be specified, too.
        division: Optional. The division for which the data should be displayed. If not specified will print all divisions.

        If one or more of the date parameters are not specified, the bot will attempt to select the best matching month.
        """
        self._log_command_use(ctx)
        utc_now = _utils.get_utc_now()
        output = []

        (month, year, division) = self.tournament_data_client.retrieve_past_parameters(ctx, month, year)
        if year is not None and month is None:
            raise _MissingParameterError('If the parameter `year` is specified, the parameter `month` must be specified, too.')

        if not _top.is_valid_division_letter(division):
            subcommand = self.bot.get_command('past stars fleet')
            await ctx.invoke(subcommand, month=month, year=year, fleet_name=division)
            return
        else:
            day, month, year = self.tournament_data_client.retrieve_past_day_month_year(month, year, utc_now)
            tourney_data = self.tournament_data_client.get_data(year, month, day=day)
            if tourney_data:
                output = await _top.get_division_stars(ctx, division=division, fleet_data=tourney_data.fleets, retrieved_date=tourney_data.retrieved_at, as_embed=(await _server_settings.get_use_embeds(ctx)))
        await _utils.discord.reply_with_output(ctx, output)


    @past_stars.command(name='fleet', aliases=['alliance'], brief='Get historic fleet stars')
    @_cooldown(rate=_BaseCog.RATE, per=_BaseCog.COOLDOWN, type=_BucketType.user)
    async def past_stars_fleet(self, ctx: _Context, month: str = None, year: str = None, *, fleet_name: str = None):
        """
        Get historic tournament fleet stars data.

        Parameters:
        month:      Optional. The month for which the data should be retrieved. Can be a number from 1 to 12, the month's name (January, ...) or the month's short name (Jan, ...)
        year:       Optional. The year for which the data should be retrieved. If the year is specified, the month has to be specified, too.
        fleet_name: Mandatory. The fleet for which the data should be displayed.

        If one or more of the date parameters are not specified, the bot will attempt to select the best matching month.
        """
        self._log_command_use(ctx)
        output = []
        utc_now = _utils.get_utc_now()
        (month, year, fleet_name) = self.tournament_data_client.retrieve_past_parameters(ctx, month, year)
        if year is not None and month is None:
            raise _MissingParameterError('If the parameter `year` is specified, the parameter `month` must be specified, too.')
        if not fleet_name:
            raise _MissingParameterError('The parameter `fleet_name` is mandatory.')

        day, month, year = self.tournament_data_client.retrieve_past_day_month_year(month, year, utc_now)
        tourney_data = self.tournament_data_client.get_data(year, month, day=day)

        if tourney_data is None:
            fleet_infos = []
        else:
            fleet_infos = await _fleet.get_fleet_infos_from_tourney_data_by_name(fleet_name, tourney_data.fleets)

        if fleet_infos:
            if len(fleet_infos) == 1:
                fleet_info = fleet_infos[0]
            else:
                use_pagination = await _server_settings.db_get_use_pagination(ctx.guild)
                paginator = _pagination.Paginator(ctx, fleet_name, fleet_infos, _fleet.get_fleet_search_details, use_pagination)
                _, fleet_info = await paginator.wait_for_option_selection()

            if fleet_info:
                output = await _fleet.get_fleet_users_stars_from_tournament_data(ctx, fleet_info, tourney_data.fleets, tourney_data.users, tourney_data.retrieved_at, tourney_data.max_tournament_battle_attempts, as_embed=(await _server_settings.get_use_embeds(ctx)))
        else:
            leading_space_note = ''
            if fleet_name.startswith(' '):
                leading_space_note = '\n**Note:** on some devices, leading spaces won\'t show. Please check, if you\'ve accidently added _two_ spaces in front of the fleet name.'
            raise _NotFound(f'Could not find a fleet named `{fleet_name}` that participated in the {year} {_calendar.month_name[int(month)]} tournament.{leading_space_note}')
        await _utils.discord.reply_with_output(ctx, output)


    @past.command(name='fleet', aliases=['alliance'], brief='Get historic fleet data')
    @_cooldown(rate=_BaseCog.RATE, per=_BaseCog.COOLDOWN, type=_BucketType.user)
    async def past_fleet(self, ctx: _Context, month: str = None, year: str = None, *, fleet_name: str = None):
        """
        Get historic tournament fleet data.

        Parameters:
        month:      Optional. The month for which the data should be retrieved. Can be a number from 1 to 12, the month's name (January, ...) or the month's short name (Jan, ...)
        year:       Optional. The year for which the data should be retrieved. If the year is specified, the month has to be specified, too.
        fleet_name: Mandatory. The fleet for which the data should be displayed.

        If one or more of the date parameters are not specified, the bot will attempt to select the best matching month.
        """
        self._log_command_use(ctx)
        error = None
        utc_now = _utils.get_utc_now()
        (month, year, fleet_name) = self.tournament_data_client.retrieve_past_parameters(ctx, month, year)
        if year is not None and month is None:
            raise _MissingParameterError('If the parameter `year` is specified, the parameter `month` must be specified, too.')
        if not fleet_name:
            raise _MissingParameterError('The parameter `fleet_name` is mandatory.')

        day, month, year = self.tournament_data_client.retrieve_past_day_month_year(month, year, utc_now)
        tourney_data = self.tournament_data_client.get_data(year, month, day=day)

        if tourney_data is None:
            fleet_infos = []
        else:
            fleet_infos = await _fleet.get_fleet_infos_from_tourney_data_by_name(fleet_name, tourney_data.fleets)

        if fleet_infos:
            if len(fleet_infos) == 1:
                fleet_info = fleet_infos[0]
            else:
                use_pagination = await _server_settings.db_get_use_pagination(ctx.guild)
                paginator = _pagination.Paginator(ctx, fleet_name, fleet_infos, _fleet.get_fleet_search_details, use_pagination)
                _, fleet_info = await paginator.wait_for_option_selection()

            if fleet_info:
                as_embed = await _server_settings.get_use_embeds(ctx)
                output, file_paths = await _fleet.get_full_fleet_info_as_text(ctx, fleet_info, past_fleets_data=tourney_data.fleets, past_users_data=tourney_data.users, past_retrieved_at=tourney_data.retrieved_at, as_embed=as_embed)
                await _utils.discord.reply_with_output_and_files(ctx, output, file_paths, output_is_embeds=as_embed)
                for file_path in file_paths:
                    _os.remove(file_path)
        elif error:
            raise _Error(str(error))
        else:
            leading_space_note = ''
            if fleet_name.startswith(' '):
                leading_space_note = '\n**Note:** on some devices, leading spaces won\'t show. Please check, if you\'ve accidently added _two_ spaces in front of the fleet name.'
            raise _NotFound(f'Could not find a fleet named `{fleet_name}` that participated in the {year} {_calendar.month_name[int(month)]} tournament.{leading_space_note}')


    @past.command(name='fleets', aliases=['alliances'], brief='Get historic fleet data', hidden=True)
    @_cooldown(rate=_BaseCog.RATE, per=_BaseCog.COOLDOWN, type=_BucketType.user)
    async def past_fleets(self, ctx: _Context, month: str = None, year: str = None):
        """
        Get historic tournament fleet data.

        Parameters:
        month:      Optional. The month for which the data should be retrieved. Can be a number from 1 to 12, the month's name (January, ...) or the month's short name (Jan, ...)
        year:       Optional. The year for which the data should be retrieved. If the year is specified, the month has to be specified, too.
        fleet_name: Mandatory. The fleet for which the data should be displayed.

        If one or more of the date parameters are not specified, the bot will attempt to select the best matching month.
        """
        self._log_command_use(ctx)
        error = None
        utc_now = _utils.get_utc_now()
        (month, year, _) = self.tournament_data_client.retrieve_past_parameters(ctx, month, year)
        if year is not None and month is None:
            raise _MissingParameterError('If the parameter `year` is specified, the parameter `month` must be specified, too.')

        day, month, year = self.tournament_data_client.retrieve_past_day_month_year(month, year, utc_now)
        tourney_data = self.tournament_data_client.get_data(year, month, day=day)

        if tourney_data and tourney_data.fleets and tourney_data.users:
            file_name = f'tournament_results_{year}-{_utils.datetime.get_month_short_name(tourney_data.retrieved_at).lower()}.csv'
            file_paths = [_fleet.create_fleets_sheet_csv(tourney_data.users, tourney_data.retrieved_at, file_name)]
            await _utils.discord.reply_with_output_and_files(ctx, [], file_paths)
            for file_path in file_paths:
                _os.remove(file_path)
        elif error:
            raise _Error(str(error))
        else:
            raise _Error(f'An error occured while retrieving tournament results for the {year} {_calendar.month_name[int(month)]} tournament. Please contact the bot\'s author!')


    @past.command(name='player', aliases=['user'], brief='Get historic player data')
    @_cooldown(rate=_BaseCog.RATE, per=_BaseCog.COOLDOWN, type=_BucketType.user)
    async def past_player(self, ctx: _Context, month: str = None, year: str = None, *, player_name: str = None):
        """
        Get historic tournament player data.

        Parameters:
        month:       Optional. The month for which the data should be retrieved. Can be a number from 1 to 12, the month's name (January, ...) or the month's short name (Jan, ...)
        year:        Optional. The year for which the data should be retrieved. If the year is specified, the month has to be specified, too.
        player_name: Mandatory. The player for which the data should be displayed.

        If one or more of the date parameters are not specified, the bot will attempt to select the best matching month.
        """
        self._log_command_use(ctx)
        output = []
        error = None
        utc_now = _utils.get_utc_now()
        (month, year, player_name) = self.tournament_data_client.retrieve_past_parameters(ctx, month, year)
        if year is not None and month is None:
            raise _MissingParameterError('If the parameter `year` is specified, the parameter `month` must be specified, too.')
        if not player_name:
            raise _MissingParameterError('The parameter `player_name` is mandatory.')

        day, month, year = self.tournament_data_client.retrieve_past_day_month_year(month, year, utc_now)
        try:
            tourney_data = self.tournament_data_client.get_data(year, month, day=day)
        except ValueError as err:
            error = str(err)
            tourney_data = None

        if tourney_data is None:
            user_infos = []
        else:
            user_infos = await _user.get_user_infos_from_tournament_data_by_name(player_name, tourney_data.users)

        if user_infos:
            if len(user_infos) == 1:
                user_info = user_infos[0]
            else:
                use_pagination = await _server_settings.db_get_use_pagination(ctx.guild)
                paginator = _pagination.Paginator(ctx, player_name, user_infos, _user.get_user_search_details, use_pagination)
                _, user_info = await paginator.wait_for_option_selection()

            if user_info:
                output = await _user.get_user_details_by_info(ctx, user_info, retrieved_at=tourney_data.retrieved_at, past_fleet_infos=tourney_data.fleets, as_embed=(await _server_settings.get_use_embeds(ctx)))
        elif error:
            raise _Error(str(error))
        else:
            leading_space_note = ''
            if player_name.startswith(' '):
                leading_space_note = '\n**Note:** on some devices, leading spaces won\'t show. Please check, if you\'ve accidently added _two_ spaces in front of the fleet name.'
            raise _NotFound(f'Could not find a player named `{player_name}` that participated in the {year} {_calendar.month_name[int(month)]} tournament.{leading_space_note}')
        await _utils.discord.reply_with_output(ctx, output)


    @_command_group(name='yesterday', brief='Get yesterday\'s tourney results', invoke_without_command=True)
    @_cooldown(rate=_BaseCog.RATE, per=_BaseCog.COOLDOWN, type=_BucketType.user)
    async def cmd_yesterday(self, ctx: _Context) -> None:
        """
        Get yesterday's final tournament standings.

        Usage:
        Use one of the subcommands.
        """
        if ctx.invoked_subcommand is None:
            await ctx.send_help('yesterday')


    @cmd_yesterday.command(name='fleet', aliases=['alliance'], brief='Get yesterday\'s fleet data')
    @_cooldown(rate=_BaseCog.RATE, per=_BaseCog.COOLDOWN, type=_BucketType.user)
    async def cmd_yesterday_fleet(self, ctx: _Context, *, fleet_name: str = None):
        """
        Get yesterday's tournament fleet data.

        Parameters:
        fleet_name: Mandatory. The fleet for which the data should be displayed.
        """
        self._log_command_use(ctx)
        utc_now = _utils.get_utc_now()
        tourney_day = _tourney.get_tourney_day(utc_now)
        if tourney_day is None:
            raise _Error('There\'s no tournament running currently.')
        if not tourney_day:
            raise _Error('It\'s day 1 of the current tournament, there is no data from yesterday.')
        output = []

        yesterday_tourney_data = self.tournament_data_client.get_latest_daily_data()
        if yesterday_tourney_data is None:
            yesterday_fleet_infos = []
        else:
            yesterday_fleet_infos = await _fleet.get_fleet_infos_from_tourney_data_by_name(fleet_name, yesterday_tourney_data.fleets)

        if yesterday_fleet_infos:
            if len(yesterday_fleet_infos) == 1:
                fleet_info = yesterday_fleet_infos[0]
            else:
                use_pagination = await _server_settings.db_get_use_pagination(ctx.guild)
                paginator = _pagination.Paginator(ctx, fleet_name, yesterday_fleet_infos, _fleet.get_fleet_search_details, use_pagination)
                _, fleet_info = await paginator.wait_for_option_selection()

            if fleet_info:
                fleet_id = fleet_info[_fleet.FLEET_KEY_NAME]
                day_before_tourney_data = self.tournament_data_client.get_second_latest_daily_data()
                yesterday_users_data = {user_id: user_info for user_id, user_info in yesterday_tourney_data.users.items() if user_info[_fleet.FLEET_KEY_NAME] == fleet_id}
                day_before_users_data = {user_id: user_info for user_id, user_info in day_before_tourney_data.users.items() if user_info[_fleet.FLEET_KEY_NAME] == fleet_id}
                for yesterday_user_info in yesterday_users_data.values():
                    day_before_user_info = day_before_users_data.get(yesterday_user_info[_user.USER_KEY_NAME], {})
                    day_before_star_count = day_before_user_info.get('AllianceScore', 0)
                    yesterday_user_info['StarValue'], _ = _user.get_star_value_from_user_info(yesterday_user_info, star_count=day_before_star_count)
                as_embed = await _server_settings.get_use_embeds(ctx)
                output, file_paths = await _fleet.get_full_fleet_info_as_text(ctx, fleet_info, max_tourney_battle_attempts=6, past_fleets_data=yesterday_tourney_data.fleets, past_users_data=yesterday_users_data, past_retrieved_at=yesterday_tourney_data.retrieved_at, as_embed=as_embed)
                await _utils.discord.reply_with_output_and_files(ctx, output, file_paths, output_is_embeds=as_embed)
                for file_path in file_paths:
                    _os.remove(file_path)
        else:
            leading_space_note = ''
            if fleet_name.startswith(' '):
                leading_space_note = '\n**Note:** on some devices, leading spaces won\'t show. Please check, if you\'ve accidently added _two_ spaces in front of the fleet name.'
            raise _NotFound(f'Could not find a fleet named `{fleet_name}` participating in current tournament.{leading_space_note}')


    @cmd_yesterday.command(name='player', aliases=['user'], brief='Get yesterday\'s player data')
    @_cooldown(rate=_BaseCog.RATE, per=_BaseCog.COOLDOWN, type=_BucketType.user)
    async def cmd_yesterday_player(self, ctx: _Context, *, player_name: str = None):
        """
        Get historic tournament player data.

        Parameters:
        player_name: Mandatory. The player for which the data should be displayed.
        """
        self._log_command_use(ctx)
        utc_now = _utils.get_utc_now()
        tourney_day = _tourney.get_tourney_day(utc_now)
        if tourney_day is None:
            raise _Error('There\'s no tournament running currently.')
        if not tourney_day:
            raise _Error('It\'s day 1 of the current tournament, there is no data from yesterday.')
        output = []

        yesterday_tourney_data = self.tournament_data_client.get_latest_daily_data()
        if yesterday_tourney_data is None:
            user_infos = []
        else:
            user_infos = await _user.get_user_infos_from_tournament_data_by_name(player_name, yesterday_tourney_data.users)

        if user_infos:
            if len(user_infos) == 1:
                user_info = user_infos[0]
            else:
                use_pagination = await _server_settings.db_get_use_pagination(ctx.guild)
                paginator = _pagination.Paginator(ctx, player_name, user_infos, _user.get_user_search_details, use_pagination)
                _, user_info = await paginator.wait_for_option_selection()

            if user_info:
                output = await _user.get_user_details_by_info(ctx, user_info, retrieved_at=yesterday_tourney_data.retrieved_at, past_fleet_infos=yesterday_tourney_data.fleets, as_embed=(await _server_settings.get_use_embeds(ctx)))
        else:
            leading_space_note = ''
            if player_name.startswith(' '):
                leading_space_note = '\n**Note:** on some devices, leading spaces won\'t show. Please check, if you\'ve accidently added _two_ spaces in front of the fleet name.'
            raise _NotFound(f'Could not find a player named `{player_name}` participating in the current tournament.{leading_space_note}')
        await _utils.discord.reply_with_output(ctx, output)


    @cmd_yesterday.group(name='stars', brief='Get yesterday\'s division stars', invoke_without_command=True)
    @_cooldown(rate=_BaseCog.RATE, per=_BaseCog.COOLDOWN, type=_BucketType.user)
    async def cmd_yesterday_stars(self, ctx: _Context, *, division: str = None):
        """
        Get yesterday's final tournament division standings.
        """
        self._log_command_use(ctx)
        utc_now = _utils.get_utc_now()
        tourney_day = _tourney.get_tourney_day(utc_now)
        if tourney_day is None:
            raise _Error('There\'s no tournament running currently.')
        if not tourney_day:
            raise _Error('It\'s day 1 of the current tournament, there is no data from yesterday.')
        output = []

        if not _top.is_valid_division_letter(division):
            subcommand = self.bot.get_command('yesterday stars fleet')
            await ctx.invoke(subcommand, fleet_name=division)
            return
        else:
            yesterday_tourney_data = self.tournament_data_client.get_latest_daily_data()
            if yesterday_tourney_data:
                output = await _top.get_division_stars(ctx, division=division, fleet_data=yesterday_tourney_data.fleets, retrieved_date=yesterday_tourney_data.retrieved_at, as_embed=(await _server_settings.get_use_embeds(ctx)))
        await _utils.discord.reply_with_output(ctx, output)


    @cmd_yesterday_stars.command(name='fleet', aliases=['alliance'], brief='Get yesterday\'s fleet stars')
    @_cooldown(rate=_BaseCog.RATE, per=_BaseCog.COOLDOWN, type=_BucketType.user)
    async def cmd_yesterday_stars_fleet(self, ctx: _Context, *, fleet_name: str = None):
        """
        Get yesterday's final tournament fleet standings.

        Parameters:
        fleet_name: Mandatory. The fleet for which the data should be displayed.
        """
        self._log_command_use(ctx)
        utc_now = _utils.get_utc_now()
        tourney_day = _tourney.get_tourney_day(utc_now)
        if tourney_day is None:
            raise _Error('There\'s no tournament running currently.')
        if not tourney_day:
            raise _Error('It\'s day 1 of the current tournament, there is no data from yesterday.')
        output = []

        yesterday_tourney_data = self.tournament_data_client.get_latest_daily_data()
        if yesterday_tourney_data is None:
            fleet_infos = []
        else:
            fleet_infos = await _fleet.get_fleet_infos_from_tourney_data_by_name(fleet_name, yesterday_tourney_data.fleets)

        if fleet_infos:
            if len(fleet_infos) == 1:
                fleet_info = fleet_infos[0]
            else:
                use_pagination = await _server_settings.db_get_use_pagination(ctx.guild)
                paginator = _pagination.Paginator(ctx, fleet_name, fleet_infos, _fleet.get_fleet_search_details, use_pagination)
                _, fleet_info = await paginator.wait_for_option_selection()

            if fleet_info:
                output = await _fleet.get_fleet_users_stars_from_tournament_data(ctx, fleet_info, yesterday_tourney_data.fleets, yesterday_tourney_data.users, yesterday_tourney_data.retrieved_at, yesterday_tourney_data.max_tournament_battle_attempts, as_embed=(await _server_settings.get_use_embeds(ctx)))
        else:
            leading_space_note = ''
            if fleet_name.startswith(' '):
                leading_space_note = '\n**Note:** on some devices, leading spaces won\'t show. Please check, if you\'ve accidently added _two_ spaces in front of the fleet name.'
            raise _NotFound(f'Could not find a fleet named `{fleet_name}` participating in the current tournament.{leading_space_note}')
        await _utils.discord.reply_with_output(ctx, output)





def setup(bot: _Bot):
    bot.add_cog(TournamentDataCog(bot))