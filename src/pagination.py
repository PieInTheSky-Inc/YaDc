import asyncio
import discord
from discord.ext.commands import Context
import math
from typing import Callable, Dict, List, Tuple

import emojis
import settings
import server_settings
import utility as util


class Paginator():
    def __init__(self, ctx: Context, search_term: str, available_options: List[dict], short_text_function: Callable[[dict], str], page_size: int = 5, timeout: float = 60.0):
        self.__context = ctx
        self.__search_term = search_term
        self.__available_options = list(available_options)
        self.__short_text_function = short_text_function
        self.__page_size = page_size
        self.__timeout = timeout

        self.__is_dm_channel = ctx.channel.type == discord.ChannelType.private
        if ctx.channel.type == discord.ChannelType.text and ctx.guild and ctx.guild.id:
            bot_permissions = ctx.me.permissions_in(ctx.channel)
            if bot_permissions.add_reactions:
                self.__use_emojis = server_settings.db_get_use_pagination(ctx.guild.id)
            else:
                self.__use_emojis = False
        else:
            self.__use_emojis = not self.__is_dm_channel

        if not self.__use_emojis:
            self.__page_size = len(self.__available_options)
            self.__base_reaction_emojis = []

        self.__pages = Paginator.__get_pages(self.__available_options, self.__page_size)
        self.__page_count = len(self.__pages)
        self.__current_page = []
        self.__current_page_no = 0
        self.__current_options: Dict[str, dict] = {}
        self.__set_first_page()
        self.__message: discord.Message = None
        self.__title = Paginator.__get_title(search_term)
        if self.__use_emojis:
            self.__base_reaction_emojis = Paginator.__get_base_reaction_emojis(self.__pages)



    async def wait_for_option_selection(self) -> (bool, dict):
        def emoji_selection_check(reaction: discord.Reaction, user: discord.User):
            if user != self.__context.bot.user:
                emoji = str(reaction.emoji)
                if (emoji in self.__current_options.keys() or emoji in self.__base_reaction_emojis) and self.__message.id == reaction.message.id:
                    return True
            return False

        def option_selection_check(message: discord.Message):
            if message.author == self.__context.author:
                return True
            return False

        repost_page = False
        await self.__post_current_page()

        while True:
            if repost_page:
                await self.__post_current_page()

            repost_page = self.__use_emojis
            reaction = None
            user = None
            reply: discord.Message = None

            try:
                if self.__use_emojis:
                    reaction, user = await self.__context.bot.wait_for('reaction_add', timeout=self.__timeout, check=emoji_selection_check)
                else:
                    reply = await self.__context.bot.wait_for('message', timeout=self.__timeout, check=option_selection_check)
            except asyncio.TimeoutError:
                self.__try_delete_message()
                return False, {}
            else:
                if reaction and user:
                    if user != self.__context.author:
                        await util.try_remove_reaction(reaction, user)
                        repost_page = False
                    else:
                        emoji = str(reaction.emoji)
                        if emoji == emojis.page_next:
                            await util.try_remove_reaction(reaction, user)
                            self.__set_next_page()
                        elif emoji == emojis.page_previous:
                            await util.try_remove_reaction(reaction, user)
                            self.__set_previous_page()
                        else:
                            await self.__try_delete_message()
                            return True, self.__current_options[emoji]
                elif reply:
                    content = str(reply.content)
                    try:
                        selection = int(content)
                    except ValueError:
                        pass
                    else:
                        if selection in self.__current_options.keys():
                            await util.try_delete_message(reply)
                            await self.__try_delete_message()
                            return True, self.__current_options[selection]


    async def __post_current_page(self) -> None:
        options_display = Paginator.__get_options_display(self.__current_page, self.__short_text_function)
        if self.__page_count > 1:
            page_no = f'page {self.__current_page_no}/{self.__page_count}'
        else:
            page_no = ''
        content = f'{self.__title}```{options_display}```{page_no}'
        if self.__message:
            if self.__page_count > 1:
                await self.__message.edit(content=content)
        else:
            self.__message = await self.__context.send(content)
            if self.__use_emojis:
                for base_reaction_emoji in self.__base_reaction_emojis:
                    await self.__message.add_reaction(base_reaction_emoji)
                for option_emoji in self.__current_options.keys():
                    await self.__message.add_reaction(option_emoji)


    def __set_first_page(self) -> None:
        new_page, new_page_no = Paginator.__get_first_page(self.__pages)
        self.__set_page(new_page)
        self.__current_page_no = new_page_no


    def __set_next_page(self) -> None:
        new_page, new_page_no = Paginator.__get_next_page(self.__pages, self.__current_page_no)
        self.__set_page(new_page)
        self.__current_page_no = new_page_no


    def __set_page(self, page: List[dict]) -> None:
        self.__current_page = page
        self.__current_options = Paginator.__get_options(page, self.__use_emojis)


    def __set_previous_page(self) -> None:
        new_page, new_page_no = Paginator.__get_previous_page(self.__pages, self.__current_page_no)
        self.__set_page(new_page)
        self.__current_page_no = new_page_no


    async def __try_delete_message(self) -> bool:
        result = await util.try_delete_message(self.__message)
        if result:
            self.__message = None
        return result


    @staticmethod
    def __get_base_reaction_emojis(pages: List[List[dict]]) -> List[str]:
        if pages and len(pages) > 1:
            return [emojis.page_previous, emojis.page_next]
        else:
            return []


    @staticmethod
    def __get_first_page(pages: List[List[dict]]) -> (List[dict], int):
        if pages:
            return pages[0], 1
        else:
            return [], 0


    @staticmethod
    def __get_next_page(pages: List[List[dict]], current_page_no: int) -> (List[dict], int):
        if pages:
            if len(pages) > current_page_no:
                current_page_no += 1
            else:
                current_page_no = 1
            return pages[current_page_no - 1], current_page_no
        else:
            return [], 0


    @staticmethod
    def __get_pages(available_options: List[dict], page_size: int) -> List[List[dict]]:
        result = []
        option_count = len(available_options)
        page_count = math.ceil(option_count / page_size)
        for page_no in range(0, page_count):
            current_page = []
            for i in range(0, page_size):
                element_at = page_no * page_size + i
                if element_at < option_count:
                    current_page.append(available_options[element_at])
                else:
                    break
            result.append(current_page)
        return result


    @staticmethod
    def __get_options(current_page: List[dict], use_emojis: bool) -> Dict[str, dict]:
        result = {}
        for i, option in enumerate(current_page):
            if use_emojis:
                emoji = emojis.options[i]
                result[emoji] = option
            else:
                result[i + 1] = option
        return result


    @staticmethod
    def __get_options_display(entity_infos: List[dict], short_text_function: Callable[[dict], str]) -> str:
        options = []
        for i, entity_info in enumerate(entity_infos, 1):
            number = str(i)
            short_text = short_text_function(entity_info)
            option = f'{number.rjust(2)}: {short_text}'
            options.append(option)
        return '\n'.join(options)



    @staticmethod
    def __get_previous_page(pages: List[List[dict]], current_page_no: int) -> (List[dict], int):
        if pages:
            if current_page_no > 1:
                current_page_no -= 1
            else:
                current_page_no = len(pages)
            return pages[current_page_no - 1], current_page_no
        else:
            return [], 0


    @staticmethod
    def __get_title(search_term: str):
        result = 'Multiple matches found'
        if search_term:
            result += f' while searching for **{search_term}**'
        result += ':'
        return result
