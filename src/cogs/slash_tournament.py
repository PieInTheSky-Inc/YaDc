import os as _os
from typing import Optional as _Optional

from discord import ApplicationContext as _ApplicationContext
from discord import Option as _Option
from discord import OptionChoice as _OptionChoice
from discord import SlashCommandGroup as _SlashCommandGroup
from discord.ext.commands import BucketType as _BucketType
from discord.ext.commands import cooldown as _cooldown

from .base import CogBase as _CogBase
from ..pss_exception import Error as _Error
from ..pss_exception import MissingParameterError as _MissingParameterError
from .. import pss_fleet as _fleet
from ..gdrive import TourneyData as _TourneyData
from .. import pss_lookups as _lookups
from .. import pss_sprites as _sprites
from .. import pss_top as _top
from .. import pss_tournament as _tourney
from .. import pss_user as _user
from .. import server_settings as _server_settings
from .. import utils as _utils
from ..yadc_bot import YadcBot as _YadcBot



class TournamentSlashCog(_CogBase, name='Tournament Slash'):
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
        name: _Option(str, 'Enter fleet name.'),
        month: _Option(int, 'Select month.', choices=_PAST_MONTH_CHOICES, required=False, default=None) = None,
        year: _Option(int, 'Enter year. If entered, a month has to be selected.', min_value=2019, required=False, default=None) = None
    ):
        """
        Get historic tournament fleet data.
        """
        self._log_command_use(ctx)

        tourney_data = await self._get_tourney_data(ctx, month, year)
        fleet_info, response = await _fleet.find_tournament_fleet(ctx, name, tourney_data)

        output, file_paths = await _fleet.get_full_fleet_info_as_text(ctx, fleet_info, past_fleets_data=tourney_data.fleets, past_users_data=tourney_data.users, past_retrieved_at=tourney_data.retrieved_at, as_embed=(await _server_settings.get_use_embeds(ctx)))
        await _utils.discord.edit_original_response(ctx, response, output=output, file_paths=file_paths)

        for file_path in file_paths:
            _os.remove(file_path)


    @past_slash.command(name='player', brief='Get historic player data')
    @_cooldown(rate=_CogBase.RATE, per=_CogBase.COOLDOWN, type=_BucketType.user)
    async def past_player_slash(self,
        ctx: _ApplicationContext,
        name: _Option(str, 'Enter player name.'),
        month: _Option(int, 'Select month.', choices=_PAST_MONTH_CHOICES, required=False, default=None) = None,
        year: _Option(int, 'Enter year. If entered, a month has to be selected.', min_value=2019, required=False, default=None) = None
    ):
        """
        Get historic tournament player data.
        """
        self._log_command_use(ctx)

        tourney_data = await self._get_tourney_data(ctx, month, year)
        user_info, response = await _user.find_tournament_user(ctx, name, tourney_data)

        output = await _user.get_user_details_by_info(ctx, user_info, retrieved_at=tourney_data.retrieved_at, past_fleet_infos=tourney_data.fleets, as_embed=(await _server_settings.get_use_embeds(ctx)))
        await _utils.discord.edit_original_response(ctx, response, output=output)


    def _assure_yesterday_command_valid(self) -> None:
        tourney_day = _tourney.get_tourney_day(_utils.get_utc_now())
        if tourney_day is None:
            raise _Error('There\'s no tournament running currently.')
        if tourney_day == 0:
            raise _Error('It\'s day 1 of the current tournament, there is no data from yesterday.')


    @past_slash.command(name='stars', brief='Get historic division stars')
    @_cooldown(rate=_CogBase.RATE, per=_CogBase.COOLDOWN, type=_BucketType.user)
    async def past_stars_slash(self,
        ctx: _ApplicationContext,
        division: _Option(str, 'Select division.', choices=_top.DIVISION_CHOICES, default=None, required=False) = None,
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


    @past_slash.command(name='starsfleet', brief='Get historic fleet stars')
    @_cooldown(rate=_CogBase.RATE, per=_CogBase.COOLDOWN, type=_BucketType.user)
    async def past_starsfleet_slash(self,
        ctx: _ApplicationContext,
        name: _Option(str, 'Enter fleet name.'),
        month: _Option(int, 'Select month.', choices=_PAST_MONTH_CHOICES, required=False, default=None) = None,
        year: _Option(int, 'Enter year. If entered, a month has to be selected.', min_value=2019, required=False, default=None) = None
    ):
        """
        Get historic tournament fleet stars data.
        """
        self._log_command_use(ctx)

        tourney_data = await self._get_tourney_data(ctx, month, year)
        fleet_info, response = await _fleet.find_tournament_fleet(ctx, name, tourney_data)
        output = await _fleet.get_fleet_users_stars_from_tournament_data(ctx, fleet_info, tourney_data.fleets, tourney_data.users, tourney_data.retrieved_at, tourney_data.max_tournament_battle_attempts, as_embed=(await _server_settings.get_use_embeds(ctx)))
        await _utils.discord.edit_original_response(ctx, response, output)


    #past_top_slash: _SlashCommandGroup = _SlashCommandGroup('top', 'Get past top players', parent=past_slash)

    @past_slash.command(name='top', brief='Get historic top captains')
    @_cooldown(rate=_CogBase.RATE, per=_CogBase.COOLDOWN, type=_BucketType.user)
    async def past_top_players_slash(self,
        ctx: _ApplicationContext,
        count: _Option(int, 'Enter number of players to be displayed', min_value=1, max_value=100, required=False, default=100) = 100,
        month: _Option(int, 'Select month.', choices=_PAST_MONTH_CHOICES, required=False, default=None) = None,
        year: _Option(int, 'Enter year. If entered, a month has to be selected.', min_value=2019, required=False, default=None) = None
    ):
        """
        Get historic top captains.
        """
        self._log_command_use(ctx)

        tourney_data = await self._get_tourney_data(ctx, month, year)
        output = await _top.get_top_captains(ctx, count, as_embed=(await _server_settings.get_use_embeds(ctx)), past_users_data=tourney_data.top_100_users)
        await _utils.discord.respond_with_output(ctx, output)


    targets_slash: _SlashCommandGroup = _SlashCommandGroup('targets', 'Get top tournament targets')

    @targets_slash.command(name='top', brief='Get top tournament targets', invoke_without_command=True)
    @_cooldown(rate=_CogBase.RATE, per=_CogBase.COOLDOWN * 2, type=_BucketType.user)
    async def targets_top_slash(self,
        ctx: _ApplicationContext,
        division: _Option(str, 'Select division.', choices=_top.DIVISION_CHOICES),
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

        star_value = _utils.format.range_string(min_star_value, max_star_value)
        trophies_value = _utils.format.range_string(min_trophies, max_trophies)
        criteria_lines, min_star_value, max_star_value, min_trophies_value, max_trophies_value, max_highest_trophies = _top.get_targets_parameters(star_value, trophies_value, max_highest_trophies)

        yesterday_tourney_data = self.bot.tournament_data_client.get_latest_daily_data()
        last_month_user_data = self.bot.tournament_data_client.get_latest_monthly_data().users
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
        division: _Option(str, 'Select division.', choices=_top.DIVISION_CHOICES),
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

        star_value = _utils.format.range_string(min_star_value, max_star_value)
        trophies_value = _utils.format.range_string(min_trophies, max_trophies)
        criteria_lines, min_star_value, max_star_value, min_trophies_value, max_trophies_value, max_highest_trophies = _top.get_targets_parameters(star_value, trophies_value, max_highest_trophies)

        max_count = _lookups.DIVISION_MAX_COUNT_TARGETS_TOP[division_design_id]
        if count:
            if count > max_count:
                count = max_count
        else:
            count = max_count

        yesterday_tourney_data = self.bot.tournament_data_client.get_latest_daily_data()
        last_month_user_data = self.bot.tournament_data_client.get_latest_monthly_data().users
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


    yesterday_slash: _SlashCommandGroup = _SlashCommandGroup('yesterday', 'Get yesterday\'s tournament data')

    @yesterday_slash.command(name='fleet', brief='Get yesterday\'s fleet data')
    @_cooldown(rate=_CogBase.RATE, per=_CogBase.COOLDOWN, type=_BucketType.user)
    async def yesterday_fleet_slash(self,
        ctx: _ApplicationContext,
        name: _Option(str, 'Enter fleet name.'),
    ):
        """
        Get yesterday's tournament fleet data.
        """
        self._log_command_use(ctx)
        self._assure_yesterday_command_valid()

        yesterday_tourney_data = await self._get_yesterday_tourney_data(ctx)
        fleet_info, response = await _fleet.find_tournament_fleet(ctx, name, yesterday_tourney_data)

        await _utils.discord.edit_original_response(ctx, response, content='Fleet found. Compiling fleet info...', embeds=[], view=None)

        fleet_id = fleet_info[_fleet.FLEET_KEY_NAME]
        day_before_tourney_data = self.bot.tournament_data_client.get_second_latest_daily_data()
        yesterday_users_data = {user_id: user_info for user_id, user_info in yesterday_tourney_data.users.items() if user_info[_fleet.FLEET_KEY_NAME] == fleet_id}
        day_before_users_data = {user_id: user_info for user_id, user_info in day_before_tourney_data.users.items() if user_info[_fleet.FLEET_KEY_NAME] == fleet_id}

        for yesterday_user_info in yesterday_users_data.values():
            day_before_user_info = day_before_users_data.get(yesterday_user_info[_user.USER_KEY_NAME], {})
            day_before_star_count = day_before_user_info.get('AllianceScore', 0)
            yesterday_user_info['StarValue'], _ = _user.get_star_value_from_user_info(yesterday_user_info, star_count=day_before_star_count)
        max_tourney_battle_attempts = (await _tourney.get_max_tourney_battle_attempts())
        output, file_paths = await _fleet.get_full_fleet_info_as_text(ctx, fleet_info, max_tourney_battle_attempts=max_tourney_battle_attempts, past_fleets_data=yesterday_tourney_data.fleets, past_users_data=yesterday_users_data, past_retrieved_at=yesterday_tourney_data.retrieved_at, as_embed=(await _server_settings.get_use_embeds(ctx)))

        await _utils.discord.edit_original_response(ctx, response, output=output, file_paths=file_paths)
        for file_path in file_paths:
            _os.remove(file_path)


    @yesterday_slash.command(name='player', brief='Get yesterday\'s player data')
    @_cooldown(rate=_CogBase.RATE, per=_CogBase.COOLDOWN, type=_BucketType.user)
    async def yesterday_player_slash(self,
        ctx: _ApplicationContext,
        name: _Option(str, 'Enter player name.')
    ):
        """
        Get yesterday's tournament player data.
        """
        self._log_command_use(ctx)
        self._assure_yesterday_command_valid()

        yesterday_tourney_data = await self._get_yesterday_tourney_data(ctx)
        user_info, response = await _user.find_tournament_user(ctx, name, yesterday_tourney_data)

        await _utils.discord.edit_original_response(ctx, response, content='Player found. Compiling player info...', embeds=[], view=None)
        output = await _user.get_user_details_by_info(ctx, user_info, retrieved_at=yesterday_tourney_data.retrieved_at, past_fleet_infos=yesterday_tourney_data.fleets, as_embed=(await _server_settings.get_use_embeds(ctx)))
        await _utils.discord.edit_original_response(ctx, response, output=output)


    yesterday_stars_slash: _SlashCommandGroup = yesterday_slash.create_subgroup('stars', 'Get yesterday\'s division stars')

    @yesterday_stars_slash.command(name='division', brief='Get yesterday\'s division stars')
    @_cooldown(rate=_CogBase.RATE, per=_CogBase.COOLDOWN, type=_BucketType.user)
    async def yesterday_stars_division_slash(self,
        ctx: _ApplicationContext,
        division: _Option(str, 'Select division.', choices=_top.DIVISION_CHOICES, default=None, required=False) = None
    ):
        """
        Get yesterday's final tournament division standings.
        """
        self._log_command_use(ctx)
        self._assure_yesterday_command_valid()

        yesterday_tourney_data = await self._get_yesterday_tourney_data(ctx)
        output = await _top.get_division_stars(ctx, division=division, fleet_data=yesterday_tourney_data.fleets, retrieved_date=yesterday_tourney_data.retrieved_at, as_embed=(await _server_settings.get_use_embeds(ctx)))
        await _utils.discord.respond_with_output(ctx, output)


    @yesterday_stars_slash.command(name='fleet', brief='Get yesterday\'s fleet stars')
    @_cooldown(rate=_CogBase.RATE, per=_CogBase.COOLDOWN, type=_BucketType.user)
    async def yesterday_stars_fleet_slash(self,
        ctx: _ApplicationContext,
        name: _Option(str, 'Enter fleet name.'),
    ):
        """
        Get yesterday's final tournament fleet standings.
        """
        self._log_command_use(ctx)
        self._assure_yesterday_command_valid()

        yesterday_tourney_data = await self._get_yesterday_tourney_data(ctx)
        fleet_info, response = await _fleet.find_tournament_fleet(ctx, name, yesterday_tourney_data)

        await _utils.discord.edit_original_response(ctx, response, content='Fleet found. Compiling fleet info...', embeds=[], view=None)
        output = await _fleet.get_fleet_users_stars_from_tournament_data(ctx, fleet_info, yesterday_tourney_data.fleets, yesterday_tourney_data.users, yesterday_tourney_data.retrieved_at, yesterday_tourney_data.max_tournament_battle_attempts, as_embed=(await _server_settings.get_use_embeds(ctx)))
        await _utils.discord.edit_original_response(ctx, response, output=output)


    async def _get_tourney_data(self, ctx: _ApplicationContext, month: int, year: int) -> _TourneyData:
        if year is not None and month is None:
            raise _MissingParameterError('If the parameter `year` is specified, the parameter `month` must be specified, too.')
        output = ['Retrieving data...']
        if ctx.interaction.response.is_done():
            await _utils.discord.edit_original_response(ctx.interaction, output=output)
        else:
            await _utils.discord.respond_with_output(ctx, output)

        day, month, year = self.bot.tournament_data_client.retrieve_past_day_month_year(month, year, _utils.get_utc_now())
        return self.bot.tournament_data_client.get_data(year, month, day=day)


    async def _get_yesterday_tourney_data(self, ctx: _ApplicationContext) -> _TourneyData:
        if not ctx.interaction.response.is_done():
            await ctx.interaction.response.defer()

        return self.bot.tournament_data_client.get_latest_daily_data()





def setup(bot: _YadcBot):
    bot.add_cog(TournamentSlashCog(bot))