import calendar as _calendar
import os as _os
from typing import Optional as _Optional

from discord import ApplicationContext as _ApplicationContext
from discord import Option as _Option
from discord import OptionChoice as _OptionChoice
from discord import slash_command as _slash_command
from discord import SlashCommandGroup as _SlashCommandGroup
from discord.ext.commands import Bot as _Bot
from discord.ext.commands import group as _command_group
from discord.ext.commands import Context as _Context
from discord.ext.commands import BucketType as _BucketType
from discord.ext.commands import cooldown as _cooldown

from .base import CogBase as _CogBase
from ..pss_exception import Error as _Error
from ..pss_exception import MissingParameterError as _MissingParameterError
from ..pss_exception import NotFound as _NotFound
from .. import pss_fleet as _fleet
from ..gdrive import TourneyData as _TourneyData
from ..gdrive import TourneyDataClient as _TourneyDataClient
from .. import pagination as _pagination
from .. import pss_lookups as _lookups
from .. import pss_sprites as _sprites
from .. import pss_top as _top
from .. import pss_tournament as _tourney
from .. import pss_user as _user
from .. import settings as _settings
from .. import server_settings as _server_settings
from .. import utils as _utils



class _TournamentCogBase(_CogBase):
    TOURNAMENT_DATA_CLIENT: _TourneyDataClient = _TourneyDataClient(
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



class TournamentCog(_TournamentCogBase, name='Tournament'):
    """
    This module offers commands to get information about fleets and players from past tournaments.
    """

    @_command_group(name='past', aliases=['history'], brief='Get historic data', invoke_without_command=True)
    @_cooldown(rate=_CogBase.RATE, per=_CogBase.COOLDOWN, type=_BucketType.user)
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
    @_cooldown(rate=_CogBase.RATE, per=_CogBase.COOLDOWN, type=_BucketType.user)
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

        (month, year, division) = _TournamentCogBase.TOURNAMENT_DATA_CLIENT.retrieve_past_parameters(ctx, month, year)
        if year is not None and month is None:
            raise _MissingParameterError('If the parameter `year` is specified, the parameter `month` must be specified, too.')

        if not _top.is_valid_division_letter(division):
            subcommand = self.bot.get_command('past stars fleet')
            await ctx.invoke(subcommand, month=month, year=year, fleet_name=division)
            return
        else:
            day, month, year = _TournamentCogBase.TOURNAMENT_DATA_CLIENT.retrieve_past_day_month_year(month, year, utc_now)
            tourney_data = _TournamentCogBase.TOURNAMENT_DATA_CLIENT.get_data(year, month, day=day)
            if tourney_data:
                output = await _top.get_division_stars(ctx, division=division, fleet_data=tourney_data.fleets, retrieved_date=tourney_data.retrieved_at, as_embed=(await _server_settings.get_use_embeds(ctx)))
        await _utils.discord.reply_with_output(ctx, output)


    @past_stars.command(name='fleet', aliases=['alliance'], brief='Get historic fleet stars')
    @_cooldown(rate=_CogBase.RATE, per=_CogBase.COOLDOWN, type=_BucketType.user)
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
        (month, year, fleet_name) = _TournamentCogBase.TOURNAMENT_DATA_CLIENT.retrieve_past_parameters(ctx, month, year)
        if year is not None and month is None:
            raise _MissingParameterError('If the parameter `year` is specified, the parameter `month` must be specified, too.')
        if not fleet_name:
            raise _MissingParameterError('The parameter `fleet_name` is mandatory.')

        day, month, year = _TournamentCogBase.TOURNAMENT_DATA_CLIENT.retrieve_past_day_month_year(month, year, utc_now)
        tourney_data = _TournamentCogBase.TOURNAMENT_DATA_CLIENT.get_data(year, month, day=day)

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
    @_cooldown(rate=_CogBase.RATE, per=_CogBase.COOLDOWN, type=_BucketType.user)
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
        (month, year, fleet_name) = _TournamentCogBase.TOURNAMENT_DATA_CLIENT.retrieve_past_parameters(ctx, month, year)
        if year is not None and month is None:
            raise _MissingParameterError('If the parameter `year` is specified, the parameter `month` must be specified, too.')
        if not fleet_name:
            raise _MissingParameterError('The parameter `fleet_name` is mandatory.')

        day, month, year = _TournamentCogBase.TOURNAMENT_DATA_CLIENT.retrieve_past_day_month_year(month, year, utc_now)
        tourney_data = _TournamentCogBase.TOURNAMENT_DATA_CLIENT.get_data(year, month, day=day)

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
    @_cooldown(rate=_CogBase.RATE, per=_CogBase.COOLDOWN, type=_BucketType.user)
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
        (month, year, _) = _TournamentCogBase.TOURNAMENT_DATA_CLIENT.retrieve_past_parameters(ctx, month, year)
        if year is not None and month is None:
            raise _MissingParameterError('If the parameter `year` is specified, the parameter `month` must be specified, too.')

        day, month, year = _TournamentCogBase.TOURNAMENT_DATA_CLIENT.retrieve_past_day_month_year(month, year, utc_now)
        tourney_data = _TournamentCogBase.TOURNAMENT_DATA_CLIENT.get_data(year, month, day=day)

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
    @_cooldown(rate=_CogBase.RATE, per=_CogBase.COOLDOWN, type=_BucketType.user)
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
        (month, year, player_name) = _TournamentCogBase.TOURNAMENT_DATA_CLIENT.retrieve_past_parameters(ctx, month, year)
        if year is not None and month is None:
            raise _MissingParameterError('If the parameter `year` is specified, the parameter `month` must be specified, too.')
        if not player_name:
            raise _MissingParameterError('The parameter `player_name` is mandatory.')

        day, month, year = _TournamentCogBase.TOURNAMENT_DATA_CLIENT.retrieve_past_day_month_year(month, year, utc_now)
        try:
            tourney_data = _TournamentCogBase.TOURNAMENT_DATA_CLIENT.get_data(year, month, day=day)
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
    @_cooldown(rate=_CogBase.RATE, per=_CogBase.COOLDOWN, type=_BucketType.user)
    async def yesterday(self, ctx: _Context) -> None:
        """
        Get yesterday's final tournament standings.

        Usage:
        Use one of the subcommands.
        """
        if ctx.invoked_subcommand is None:
            await ctx.send_help('yesterday')


    @yesterday.command(name='fleet', aliases=['alliance'], brief='Get yesterday\'s fleet data')
    @_cooldown(rate=_CogBase.RATE, per=_CogBase.COOLDOWN, type=_BucketType.user)
    async def yesterday_fleet(self, ctx: _Context, *, fleet_name: str = None):
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

        yesterday_tourney_data = _TournamentCogBase.TOURNAMENT_DATA_CLIENT.get_latest_daily_data()
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
                day_before_tourney_data = _TournamentCogBase.TOURNAMENT_DATA_CLIENT.get_second_latest_daily_data()
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


    @yesterday.command(name='player', aliases=['user'], brief='Get yesterday\'s player data')
    @_cooldown(rate=_CogBase.RATE, per=_CogBase.COOLDOWN, type=_BucketType.user)
    async def yesterday_player(self, ctx: _Context, *, player_name: str = None):
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

        yesterday_tourney_data = _TournamentCogBase.TOURNAMENT_DATA_CLIENT.get_latest_daily_data()
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


    @yesterday.group(name='stars', brief='Get yesterday\'s division stars', invoke_without_command=True)
    @_cooldown(rate=_CogBase.RATE, per=_CogBase.COOLDOWN, type=_BucketType.user)
    async def yesterday_stars(self, ctx: _Context, *, division: str = None):
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
            yesterday_tourney_data = _TournamentCogBase.TOURNAMENT_DATA_CLIENT.get_latest_daily_data()
            if yesterday_tourney_data:
                output = await _top.get_division_stars(ctx, division=division, fleet_data=yesterday_tourney_data.fleets, retrieved_date=yesterday_tourney_data.retrieved_at, as_embed=(await _server_settings.get_use_embeds(ctx)))
        await _utils.discord.reply_with_output(ctx, output)


    @yesterday_stars.command(name='fleet', aliases=['alliance'], brief='Get yesterday\'s fleet stars')
    @_cooldown(rate=_CogBase.RATE, per=_CogBase.COOLDOWN, type=_BucketType.user)
    async def yesterday_stars_fleet(self, ctx: _Context, *, fleet_name: str = None):
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

        yesterday_tourney_data = _TournamentCogBase.TOURNAMENT_DATA_CLIENT.get_latest_daily_data()
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


    @_command_group(name='targets', brief='Get top tournament targets', invoke_without_command=True)
    @_cooldown(rate=_CogBase.RATE, per=_CogBase.COOLDOWN * 2, type=_BucketType.user)
    async def targets(self, ctx: _Context, division: str, star_value: str = None, trophies: str = None, max_highest_trophies: int = None) -> None:
        """
        Prints a list of highest value tournament targets with a minimum star value and a maximum trophy count.

        Usage:
        /targets [division] <mininum star value> <maximum trophy count>

        Parameters:
        division:       Mandatory. The letter of the tournament division.
        star_value:     Optional. The minimum (and maximum) star value to be considered. Accepts a range.
        trophies:       Optional. The (minimum and) maximum trophy count to be considered. Accepts a range.
        max_trophies:   Optional. The highest trophy count a player ever had for them to be considered.

        Examples:
        /targets a - Prints the top 100 players in division A by highest star value
        /targets a 5 - Prints up to the top 100 players in division A with a star value of at least 5
        /targets a 5 3000 - Prints up to the top 100 players in division A with a star value of at least 5 and max 3k trophies currently
        /targets a 5 3000 5000 - Prints up to the top 100 players in division A with a star value of at least 5, max 3k trophies currently and with a highest trophy count of 5k
        /targets a 5-10 3000-4000 - Prints up to the top 100 players in division A with a star value of 5 to 10 and 3k to 4k trophies currently
        /targets a 5-10 3000-4000 5000 - Prints up to the top 100 players in division A with a star value of 5 to 10 and 3k to 4k trophies currently and with a highest trophy count of 5k
        """
        if ctx.invoked_subcommand is None:
            self._log_command_use(ctx)
            #if not tourney.is_tourney_running():
            #    raise Error('There\'s no tournament running currently.')

            division_design_id = _lookups.DIVISION_CHAR_TO_DESIGN_ID.get(division.upper())
            if not division_design_id:
                raise ValueError('The specified division is not valid.')

            criteria_lines, min_star_value, max_star_value, min_trophies_value, max_trophies_value, max_highest_trophies = _top.get_targets_parameters(star_value, trophies, max_highest_trophies)

            yesterday_tourney_data = _TournamentCogBase.TOURNAMENT_DATA_CLIENT.get_latest_daily_data()
            last_month_user_data = _TournamentCogBase.TOURNAMENT_DATA_CLIENT.get_latest_monthly_data().users
            current_fleet_data = await _top.get_alliances_with_division()

            if yesterday_tourney_data:
                yesterday_user_infos = _top.filter_targets(yesterday_tourney_data.users.values(), division_design_id, last_month_user_data, current_fleet_data, min_star_value, max_star_value, min_trophies_value, max_trophies_value, max_highest_trophies)
                if not yesterday_user_infos:
                    error_lines = [f'No ships in division {division.upper()} match the criteria.'] + criteria_lines
                    raise _Error('\n'.join(error_lines))

                yesterday_user_infos_count = len(yesterday_user_infos)
                if yesterday_user_infos_count >= 100:
                    yesterday_user_infos = yesterday_user_infos[:100]
                    count_display_text = f'Displaying the first 100 of {yesterday_user_infos_count} matching targets.'
                else:
                    count_display_text = None

                output = []
                colour = _utils.discord.get_bot_member_colour(ctx.bot, ctx.guild)
                as_embed = await _server_settings.get_use_embeds(ctx)
                divisions_designs_infos = await _top.divisions_designs_retriever.get_data_dict3()
                footer, output_lines = _top.make_target_output_lines(yesterday_user_infos, )
                historic_data_note = _utils.datetime.get_historic_data_note(yesterday_tourney_data.retrieved_at)

                if criteria_lines or count_display_text:
                    output_lines.insert(0, '_ _')
                    for criteria_line in reversed(criteria_lines):
                        output_lines.insert(0, criteria_line)
                    if count_display_text:
                        output_lines.insert(0, count_display_text)

                if as_embed:
                    if historic_data_note:
                        footer += f'\n\n{historic_data_note}'
                    title = f'{divisions_designs_infos[division_design_id][_top.DIVISION_DESIGN_DESCRIPTION_PROPERTY_NAME]} - Top targets'
                    thumbnail_url = await _sprites.get_download_sprite_link(divisions_designs_infos[division_design_id]['BackgroundSpriteId'])
                    embed_bodies = _utils.discord.create_posts_from_lines(output_lines, _utils.discord.MAXIMUM_CHARACTERS_EMBED_DESCRIPTION)
                    for i, embed_body in enumerate(embed_bodies):
                        thumbnail_url = thumbnail_url if i == 0 else None
                        embed = _utils.discord.create_embed(title, description=embed_body, footer=footer, thumbnail_url=thumbnail_url, colour=colour)
                        output.append(embed)
                else:
                    if historic_data_note:
                        footer += f'\n\n{historic_data_note}'
                    title = f'__**{divisions_designs_infos[division_design_id][_top.DIVISION_DESIGN_DESCRIPTION_PROPERTY_NAME]} - Top targets**__'
                    output.append(title)
                    output.extend(output_lines)
                    output.append(_utils.discord.ZERO_WIDTH_SPACE)

                await _utils.discord.post_output(ctx, output)
            else:
                raise _Error('Could not retrieve yesterday\'s tournament data.')


    @targets.command(name='top', brief='Get top tournament targets')
    @_cooldown(rate=_CogBase.RATE, per=_CogBase.COOLDOWN * 2, type=_BucketType.user)
    async def targets_top(self, ctx: _Context, division: str, count: int = None, star_value: str = None, trophies: str = None, max_highest_trophies: int = None) -> None:
        """
        Prints a list of the highest value tournament targets of all fleets in a specific division with a minimum star value and a maximum trophy count.

        Usage:
        /targets top [division] <count> <mininum star value> <maximum trophy count>

        Parameters:
        division:       Mandatory. The letter of the tournament division.
        count:          Optional. The number of members to display per fleet. See below for defaults.
        star_value:     Optional. The minimum (and maximum) star value to be considered. Accepts a range.
        trophies:       Optional. The (minimum and) maximum trophy count to be considered. Accepts a range.
        max_trophies:   Optional. The highest trophy count a player ever had for them to be considered.

        Examples:
        /targets top a - Prints the top 20 players per fleet in division A by highest star value
        /targets top a 5 - Prints up to the top 5 players per fleet in division A by highest star value
        /targets top a 5 4 - Prints up to the top 5 players per fleet in division A with a star value of at least 4
        /targets top a 5 4 3000 - Prints up to the top 5 players per fleet in division A with a star value of at least 4 and max 3k trophies currently
        /targets top a 5 4 3000 5000 - Prints up to the top 5 players per fleet in division A with a star value of at least 4, max 3k trophies currently and with a highest trophy count of 5k
        /targets top a 5 4-10 3000-4000 - Prints up to the top 5 players per fleet in division A with a star value of 4 to 10 and 3k to 4k trophies currently
        /targets top a 5 4-10 3000-4000 5000 - Prints up to the top 5 players per fleet in division A with a star value of 4 to 10 and 3k to 4k trophies currently and with a highest trophy count of 5k

        Notes:
        The parameter 'count' is constrained depending on the division:
            Division A: max 20
            Division B: max 14
            Division C: max 5
            Division D: max 3
        """
        self._log_command_use(ctx)
        #if not tourney.is_tourney_running():
        #    raise Error('There\'s no tournament running currently.')

        division_design_id = _lookups.DIVISION_CHAR_TO_DESIGN_ID.get(division.upper())
        if not division_design_id:
            raise ValueError('The specified division is not valid.')

        max_count = _lookups.DIVISION_MAX_COUNT_TARGETS_TOP[division_design_id]
        if count:
            if count < 0:
                raise ValueError('The member count must not be a negative number.')
            elif count > max_count:
                raise ValueError(f'The maximum member count to be displayed for division {division.upper()} is {max_count}.')
        else:
            count = max_count

        criteria_lines, min_star_value, max_star_value, min_trophies_value, max_trophies_value, max_highest_trophies = _top.get_targets_parameters(star_value, trophies, max_highest_trophies)

        yesterday_tourney_data = _TournamentCogBase.TOURNAMENT_DATA_CLIENT.get_latest_daily_data()
        last_month_user_data = _TournamentCogBase.TOURNAMENT_DATA_CLIENT.get_latest_monthly_data().users
        current_fleet_data = await _top.get_alliances_with_division()

        if yesterday_tourney_data:
            yesterday_user_infos = _top.filter_targets(yesterday_tourney_data.users.values(), division_design_id, last_month_user_data, current_fleet_data, min_star_value, max_star_value, min_trophies_value, max_trophies_value, max_highest_trophies)
            if not yesterday_user_infos:
                error_text = [f'No ships in division {division.upper()} match the criteria.'] + criteria_lines
                raise _Error('\n'.join(error_text))

            yesterday_fleet_users_infos = {}
            for user_info in yesterday_user_infos:
                yesterday_fleet_users_infos.setdefault(user_info[_fleet.FLEET_KEY_NAME], []).append(user_info)

            for fleet_id, fleet_users_infos in yesterday_fleet_users_infos.items():
                if count < len(fleet_users_infos):
                    yesterday_fleet_users_infos[fleet_id] = fleet_users_infos[:count]

            historic_data_note = _utils.datetime.get_historic_data_note(yesterday_tourney_data.retrieved_at)
            colour = _utils.discord.get_bot_member_colour(ctx.bot, ctx.guild)
            as_embed = await _server_settings.get_use_embeds(ctx)
            divisions_designs_infos = await _top.divisions_designs_retriever.get_data_dict3()
            output_lines = []
            current_fleet_infos = sorted(current_fleet_data.values(), key=lambda fleet_info: int(fleet_info.get('Score', 0)), reverse=True)
            current_fleet_infos = [current_fleet_info for current_fleet_info in current_fleet_infos if current_fleet_info.get(_top.DIVISION_DESIGN_KEY_NAME) == division_design_id]
            for fleet_rank, current_fleet_info in enumerate(current_fleet_infos, 1):
                fleet_id = current_fleet_info[_fleet.FLEET_KEY_NAME]
                if fleet_id in yesterday_fleet_users_infos:
                    fleet_title_lines = [f'**{fleet_rank}. {current_fleet_info[_fleet.FLEET_DESCRIPTION_PROPERTY_NAME]}**']
                    footer, text_lines = _top.make_target_output_lines(yesterday_fleet_users_infos[fleet_id], include_fleet_name=False)
                    fleet_title_lines[0] += f'\n{text_lines[0]}'
                    output_lines.extend(fleet_title_lines)
                    output_lines.extend(text_lines[1:])
                    output_lines.append('')

            if criteria_lines or count:
                output_lines.insert(0, '_ _')
                for criteria_line in reversed(criteria_lines):
                    output_lines.insert(0, criteria_line)
                if count:
                    output_lines.insert(0, f'Top {count} members')

            output = []
            if as_embed:
                if historic_data_note:
                    footer += f'\n\n{historic_data_note}'
                division_title = f'{divisions_designs_infos[division_design_id][_top.DIVISION_DESIGN_DESCRIPTION_PROPERTY_NAME]} - Top targets per fleet'
                thumbnail_url = await _sprites.get_download_sprite_link(divisions_designs_infos[division_design_id]['BackgroundSpriteId'])
                embed_bodies = _utils.discord.create_posts_from_lines(output_lines, _utils.discord.MAXIMUM_CHARACTERS_EMBED_DESCRIPTION)
                for user_rank, embed_body in enumerate(embed_bodies):
                    thumbnail_url = thumbnail_url if user_rank == 0 else None
                    embed = _utils.discord.create_embed(division_title, description=embed_body, footer=footer, thumbnail_url=thumbnail_url, colour=colour)
                    output.append(embed)
            else:
                if historic_data_note:
                    footer += f'\n{historic_data_note}'
                division_title = f'__**{divisions_designs_infos[division_design_id][_top.DIVISION_DESIGN_DESCRIPTION_PROPERTY_NAME]} - Top targets per fleet**__'
                output.append(division_title)
                output.extend(output_lines)
                output.append(_utils.discord.ZERO_WIDTH_SPACE)

            await _utils.discord.post_output(ctx, output)
        else:
            raise _Error('Could not retrieve yesterday\'s tournament data.')





class TournamentSlashCog(_TournamentCogBase, name='Tournament Slash'):
    _PAST_MONTH_CHOICES = [
        _OptionChoice('January', 1),
        _OptionChoice('February', 2),
        _OptionChoice('March', 3),
        _OptionChoice('April', 4),
        _OptionChoice('May', 5),
        _OptionChoice('June', 6),
        _OptionChoice('July', 7),
        _OptionChoice('August', 8),
        _OptionChoice('September', 9),
        _OptionChoice('October', 10),
        _OptionChoice('November', 11),
        _OptionChoice('December', 12),
    ]


    past_slash: _SlashCommandGroup = _SlashCommandGroup('past', 'Get historic data')

    @past_slash.command(name='fleet', brief='Get historic fleet data')
    @_cooldown(rate=_CogBase.RATE, per=_CogBase.COOLDOWN, type=_BucketType.user)
    async def past_fleet_slash(self,
        ctx: _ApplicationContext,
        fleet_name: _Option(str, 'Enter fleet name.'),
        month: _Option(int, 'Select month.', choices=_PAST_MONTH_CHOICES, required=False, default=None) = None,
        year: _Option(int, 'Enter year. If entered, a month has to be selected.', min_value=2019, required=False, default=None) = None
    ):
        """
        Get historic tournament fleet data.
        """
        self._log_command_use(ctx)

        tourney_data = await self._get_tourney_data(ctx, month, year)
        fleet_info, response = await _fleet.find_tournament_fleet(ctx, fleet_name, tourney_data)

        output, file_paths = await _fleet.get_full_fleet_info_as_text(ctx, fleet_info, past_fleets_data=tourney_data.fleets, past_users_data=tourney_data.users, past_retrieved_at=tourney_data.retrieved_at, as_embed=(await _server_settings.get_use_embeds(ctx)))
        await _utils.discord.edit_original_message(response, output=output, file_paths=file_paths)

        for file_path in file_paths:
            _os.remove(file_path)


    @past_slash.command(name='player', brief='Get historic player data')
    @_cooldown(rate=_CogBase.RATE, per=_CogBase.COOLDOWN, type=_BucketType.user)
    async def past_player_slash(self,
        ctx: _ApplicationContext,
        player_name: _Option(str, 'Enter player name.'),
        month: _Option(int, 'Select month.', choices=_PAST_MONTH_CHOICES, required=False, default=None) = None,
        year: _Option(int, 'Enter year. If entered, a month has to be selected.', min_value=2019, required=False, default=None) = None
    ):
        """
        Get historic tournament player data.
        """
        self._log_command_use(ctx)

        await self._perform_past_player_command(ctx, player_name, month, year)


    past_stars_slash: _SlashCommandGroup = past_slash.create_subgroup('stars', 'Get historic stars')

    @past_stars_slash.command(name='division', brief='Get historic division stars')
    @_cooldown(rate=_CogBase.RATE, per=_CogBase.COOLDOWN, type=_BucketType.user)
    async def past_stars_division_slash(self,
        ctx: _ApplicationContext,
        division: _Option(str, 'Enter division letter.', choices=_top.DIVISION_CHOICES, default=None, required=False) = None,
        month: _Option(int, 'Select month.', choices=_PAST_MONTH_CHOICES, required=False, default=None) = None,
        year: _Option(int, 'Enter year. If entered, a month has to be selected.', min_value=2019, required=False, default=None) = None
    ):
        """
        Get historic tournament division stars data.
        """
        self._log_command_use(ctx)

        tourney_data = await self._get_tourney_data(ctx, month, year)
        output = await _top.get_division_stars(ctx, division=division, fleet_data=tourney_data.fleets, retrieved_date=tourney_data.retrieved_at, as_embed=(await _server_settings.get_use_embeds(ctx)))
        await _utils.discord.respond_with_output(ctx, output)


    @past_stars_slash.command(name='fleet', brief='Get historic fleet stars')
    @_cooldown(rate=_CogBase.RATE, per=_CogBase.COOLDOWN, type=_BucketType.user)
    async def past_stars_fleet_slash(self,
        ctx: _ApplicationContext,
        fleet_name: _Option(str, 'Enter fleet name.'),
        month: _Option(int, 'Select month.', choices=_PAST_MONTH_CHOICES, required=False, default=None) = None,
        year: _Option(int, 'Enter year. If entered, a month has to be selected.', min_value=2019, required=False, default=None) = None
    ):
        """
        Get historic tournament fleet stars data.
        """
        self._log_command_use(ctx)

        tourney_data = await self._get_tourney_data(ctx, month, year)
        fleet_info, response = await _fleet.find_tournament_fleet(ctx, fleet_name, tourney_data)
        output = await _fleet.get_fleet_users_stars_from_tournament_data(ctx, fleet_info, tourney_data.fleets, tourney_data.users, tourney_data.retrieved_at, tourney_data.max_tournament_battle_attempts, as_embed=(await _server_settings.get_use_embeds(ctx)))
        await _utils.discord.edit_original_message(response, output)


    @past_slash.command(name='user', brief='Get historic player data')
    @_cooldown(rate=_CogBase.RATE, per=_CogBase.COOLDOWN, type=_BucketType.user)
    async def past_user_slash(self,
        ctx: _ApplicationContext,
        player_name: _Option(str, 'Enter player name.'),
        month: _Option(int, 'Select month.', choices=_PAST_MONTH_CHOICES, required=False, default=None) = None,
        year: _Option(int, 'Enter year. If entered, a month has to be selected.', min_value=2019, required=False, default=None) = None
    ):
        """
        Get historic tournament player data.
        """
        self._log_command_use(ctx)

        await self._perform_past_player_command(ctx, player_name, month, year)


    async def _get_tourney_data(self, ctx: _ApplicationContext, month: int, year: int) -> _TourneyData:
        if year is not None and month is None:
            raise _MissingParameterError('If the parameter `year` is specified, the parameter `month` must be specified, too.')
        if not ctx.interaction.response.is_done():
            await ctx.interaction.response.defer()

        day, month, year = _TournamentCogBase.TOURNAMENT_DATA_CLIENT.retrieve_past_day_month_year(month, year, _utils.get_utc_now())
        return _TournamentCogBase.TOURNAMENT_DATA_CLIENT.get_data(year, month, day=day)


    async def _perform_past_player_command(self, ctx: _ApplicationContext, player_name: str, month: _Optional[int], year: _Optional[int]) -> None:
        tourney_data = await self._get_tourney_data(ctx, month, year)
        user_info, response = await _user.find_tournament_user(ctx, player_name, tourney_data)

        output = await _user.get_user_details_by_info(ctx, user_info, retrieved_at=tourney_data.retrieved_at, past_fleet_infos=tourney_data.fleets, as_embed=(await _server_settings.get_use_embeds(ctx)))
        await _utils.discord.edit_original_message(response, output=output)


    targets_slash: _SlashCommandGroup = _SlashCommandGroup('targets', 'Get top tournament targets')

    @targets_slash(name='top', brief='Get top tournament targets', invoke_without_command=True)
    @_cooldown(rate=_CogBase.RATE, per=_CogBase.COOLDOWN * 2, type=_BucketType.user)
    async def targets(self,
        ctx: _ApplicationContext,
        division: _Option(str, 'Enter division.', choices=_top.DIVISION_CHOICES),
        min_star_value: _Option(int, 'Enter minimum star value of target.', min_value=1, required=False) = None,
        max_star_value: _Option(int, 'Enter maximum star value of target.', min_value=1, required=False) = None,
        min_trophies: _Option(int, 'Enter minimum trophy count of target.', min_value=1, required=False) = None,
        max_trophies: _Option(int, 'Enter maximum trophy count of target.', min_value=1, required=False) = None,
        max_highest_trophies: _Option(int, 'Enter highest trophies maximum.', min_value=1000, required=False) = None
    ):
        """
        Prints a list of highest value tournament targets in a specified division.
        """
        self._log_command_use(ctx)
        if not _tourney.is_tourney_running():
            raise _Error('There\'s no tournament running currently.')

        await ctx.interaction.response.defer()
        division_design_id = _lookups.DIVISION_CHAR_TO_DESIGN_ID.get(division.upper())

        star_values = []
        if min_star_value:
            star_values.append(min_star_value)
        if max_star_value:
            star_values.append(max_star_value)
        star_value = '-'.join(sorted(star_values))
        trophies_values = []
        if min_trophies:
            trophies_values.append(min_trophies)
        if max_trophies:
            trophies_values.append(max_trophies)
        trophies_value = '-'.join(sorted(trophies_values))

        criteria_lines, min_star_value, max_star_value, min_trophies_value, max_trophies_value, max_highest_trophies = _top.get_targets_parameters(star_value, trophies_value, max_highest_trophies)

        yesterday_tourney_data = _TournamentCogBase.TOURNAMENT_DATA_CLIENT.get_latest_daily_data()
        last_month_user_data = _TournamentCogBase.TOURNAMENT_DATA_CLIENT.get_latest_monthly_data().users
        current_fleet_data = await _top.get_alliances_with_division()

        if yesterday_tourney_data:
            yesterday_user_infos = _top.filter_targets(yesterday_tourney_data.users.values(), division_design_id, last_month_user_data, current_fleet_data, min_star_value, max_star_value, min_trophies_value, max_trophies_value, max_highest_trophies)
            if not yesterday_user_infos:
                error_lines = [f'No ships in division {division.upper()} match the criteria.'] + criteria_lines
                raise _Error('\n'.join(error_lines))

            yesterday_user_infos_count = len(yesterday_user_infos)
            if yesterday_user_infos_count >= 100:
                yesterday_user_infos = yesterday_user_infos[:100]
                count_display_text = f'Displaying the first 100 of {yesterday_user_infos_count} matching targets.'
            else:
                count_display_text = None

            output = []
            colour = _utils.discord.get_bot_member_colour(ctx.bot, ctx.guild)
            as_embed = await _server_settings.get_use_embeds(ctx)
            divisions_designs_infos = await _top.divisions_designs_retriever.get_data_dict3()
            footer, output_lines = _top.make_target_output_lines(yesterday_user_infos)
            historic_data_note = _utils.datetime.get_historic_data_note(yesterday_tourney_data.retrieved_at)

            if criteria_lines or count_display_text:
                output_lines.insert(0, '_ _')
                for criteria_line in reversed(criteria_lines):
                    output_lines.insert(0, criteria_line)
                if count_display_text:
                    output_lines.insert(0, count_display_text)

            if as_embed:
                if historic_data_note:
                    footer += f'\n\n{historic_data_note}'
                title = f'{divisions_designs_infos[division_design_id][_top.DIVISION_DESIGN_DESCRIPTION_PROPERTY_NAME]} - Top targets'
                thumbnail_url = await _sprites.get_download_sprite_link(divisions_designs_infos[division_design_id]['BackgroundSpriteId'])
                embed_bodies = _utils.discord.create_posts_from_lines(output_lines, _utils.discord.MAXIMUM_CHARACTERS_EMBED_DESCRIPTION)
                for i, embed_body in enumerate(embed_bodies):
                    thumbnail_url = thumbnail_url if i == 0 else None
                    embed = _utils.discord.create_embed(title, description=embed_body, footer=footer, thumbnail_url=thumbnail_url, colour=colour)
                    output.append(embed)
            else:
                if historic_data_note:
                    footer += f'\n\n{historic_data_note}'
                title = f'__**{divisions_designs_infos[division_design_id][_top.DIVISION_DESIGN_DESCRIPTION_PROPERTY_NAME]} - Top targets**__'
                output.append(title)
                output.extend(output_lines)
                output.append(_utils.discord.ZERO_WIDTH_SPACE)

            await _utils.discord.respond_with_output(ctx, output)
        else:
            raise _Error('Could not retrieve yesterday\'s tournament data.')


    @targets_slash.command(name='fleets', brief='Get top tournament targets per fleet')
    @_cooldown(rate=_CogBase.RATE, per=_CogBase.COOLDOWN * 2, type=_BucketType.user)
    async def targets_fleets_slash(self,
        ctx: _ApplicationContext,
        division: _Option(str, 'Enter division.', choices=_top.DIVISION_CHOICES),
        count: _Option(int, 'Enter number of players per fleet to be displayed.') = None,
        min_star_value: _Option(int, 'Enter minimum star value of target.', min_value=1, required=False) = None,
        max_star_value: _Option(int, 'Enter maximum star value of target.', min_value=1, required=False) = None,
        min_trophies: _Option(int, 'Enter minimum trophy count of target.', min_value=1, required=False) = None,
        max_trophies: _Option(int, 'Enter maximum trophy count of target.', min_value=1, required=False) = None,
        max_highest_trophies: _Option(int, 'Enter highest trophies maximum.', min_value=1000, required=False) = None
    ):
        """
        Prints a list of the highest value tournament targets of all fleets in a specific division.
        """
        self._log_command_use(ctx)
        if not _tourney.is_tourney_running():
            raise _Error('There\'s no tournament running currently.')

        await ctx.interaction.response.defer()
        division_design_id = _lookups.DIVISION_CHAR_TO_DESIGN_ID.get(division.upper())

        star_values = []
        if min_star_value:
            star_values.append(min_star_value)
        if max_star_value:
            star_values.append(max_star_value)
        star_value = '-'.join(sorted(star_values))
        trophies_values = []
        if min_trophies:
            trophies_values.append(min_trophies)
        if max_trophies:
            trophies_values.append(max_trophies)
        trophies_value = '-'.join(sorted(trophies_values))

        max_count = _lookups.DIVISION_MAX_COUNT_TARGETS_TOP[division_design_id]
        if count:
            if count > max_count:
                count = max_count
        else:
            count = max_count

        criteria_lines, min_star_value, max_star_value, min_trophies_value, max_trophies_value, max_highest_trophies = _top.get_targets_parameters(star_value, trophies_value, max_highest_trophies)

        yesterday_tourney_data = _TournamentCogBase.TOURNAMENT_DATA_CLIENT.get_latest_daily_data()
        last_month_user_data = _TournamentCogBase.TOURNAMENT_DATA_CLIENT.get_latest_monthly_data().users
        current_fleet_data = await _top.get_alliances_with_division()

        if yesterday_tourney_data:
            yesterday_user_infos = _top.filter_targets(yesterday_tourney_data.users.values(), division_design_id, last_month_user_data, current_fleet_data, min_star_value, max_star_value, min_trophies_value, max_trophies_value, max_highest_trophies)
            if not yesterday_user_infos:
                error_text = [f'No ships in division {division.upper()} match the criteria.'] + criteria_lines
                raise _Error('\n'.join(error_text))

            yesterday_fleet_users_infos = {}
            for user_info in yesterday_user_infos:
                yesterday_fleet_users_infos.setdefault(user_info[_fleet.FLEET_KEY_NAME], []).append(user_info)

            for fleet_id, fleet_users_infos in yesterday_fleet_users_infos.items():
                if count < len(fleet_users_infos):
                    yesterday_fleet_users_infos[fleet_id] = fleet_users_infos[:count]

            historic_data_note = _utils.datetime.get_historic_data_note(yesterday_tourney_data.retrieved_at)
            colour = _utils.discord.get_bot_member_colour(ctx.bot, ctx.guild)
            as_embed = await _server_settings.get_use_embeds(ctx)
            divisions_designs_infos = await _top.divisions_designs_retriever.get_data_dict3()
            output_lines = []
            current_fleet_infos = sorted(current_fleet_data.values(), key=lambda fleet_info: int(fleet_info.get('Score', 0)), reverse=True)
            current_fleet_infos = [current_fleet_info for current_fleet_info in current_fleet_infos if current_fleet_info.get(_top.DIVISION_DESIGN_KEY_NAME) == division_design_id]
            for fleet_rank, current_fleet_info in enumerate(current_fleet_infos, 1):
                fleet_id = current_fleet_info[_fleet.FLEET_KEY_NAME]
                if fleet_id in yesterday_fleet_users_infos:
                    fleet_title_lines = [f'**{fleet_rank}. {current_fleet_info[_fleet.FLEET_DESCRIPTION_PROPERTY_NAME]}**']
                    footer, text_lines = _top.make_target_output_lines(yesterday_fleet_users_infos[fleet_id], include_fleet_name=False)
                    fleet_title_lines[0] += f'\n{text_lines[0]}'
                    output_lines.extend(fleet_title_lines)
                    output_lines.extend(text_lines[1:])
                    output_lines.append('')

            if criteria_lines or count:
                output_lines.insert(0, '_ _')
                for criteria_line in reversed(criteria_lines):
                    output_lines.insert(0, criteria_line)
                if count:
                    output_lines.insert(0, f'Top {count} members')

            output = []
            if as_embed:
                if historic_data_note:
                    footer += f'\n\n{historic_data_note}'
                division_title = f'{divisions_designs_infos[division_design_id][_top.DIVISION_DESIGN_DESCRIPTION_PROPERTY_NAME]} - Top targets per fleet'
                thumbnail_url = await _sprites.get_download_sprite_link(divisions_designs_infos[division_design_id]['BackgroundSpriteId'])
                embed_bodies = _utils.discord.create_posts_from_lines(output_lines, _utils.discord.MAXIMUM_CHARACTERS_EMBED_DESCRIPTION)
                for user_rank, embed_body in enumerate(embed_bodies):
                    thumbnail_url = thumbnail_url if user_rank == 0 else None
                    embed = _utils.discord.create_embed(division_title, description=embed_body, footer=footer, thumbnail_url=thumbnail_url, colour=colour)
                    output.append(embed)
            else:
                if historic_data_note:
                    footer += f'\n{historic_data_note}'
                division_title = f'__**{divisions_designs_infos[division_design_id][_top.DIVISION_DESIGN_DESCRIPTION_PROPERTY_NAME]} - Top targets per fleet**__'
                output.append(division_title)
                output.extend(output_lines)
                output.append(_utils.discord.ZERO_WIDTH_SPACE)

            await _utils.discord.respond_with_output(ctx, output)
        else:
            raise _Error('Could not retrieve yesterday\'s tournament data.')






def setup(bot: _Bot):
    if _settings.OFFER_PREFIXED_COMMANDS:
        bot.add_cog(TournamentCog(bot))
    if _settings.OFFER_SLASH_COMMANDS:
        bot.add_cog(TournamentSlashCog(bot))