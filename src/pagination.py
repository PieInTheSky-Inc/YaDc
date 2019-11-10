import asyncio
import discord
from discord.ext.commands import Context
import math
from typing import Callable, Dict, List, Tuple

import emojis


class Paginator():
    def __init__(self, ctx: Context, search_term: str, available_options: List[dict], short_text_function: Callable[[dict], str], page_size: int = 5):
        self.__context = ctx
        self.__search_term = search_term
        self.__available_options = list(available_options)
        self.__short_text_function = short_text_function
        self.__page_size = page_size

        self.__pages = Paginator.__get_pages(self.__available_options, self.__page_size)
        self.__current_page = []
        self.__current_page_no = 0
        self.__current_options: Dict[str, dict] = {}
        self.__set_first_page()
        self.__message: discord.Message = None
        self.__title = Paginator.__get_title(search_term)
        self.__base_reaction_emojis = Paginator.__get_base_reaction_emojis(self.__pages)


    async def wait_for_option_selection(self) -> (bool, dict):
        def option_selection_check(reaction: discord.Reaction, user: discord.User):
            if user == self.__context.author:
                emoji = str(reaction.emoji)
                if emoji in self.__current_options.keys() or emoji in self.__base_reaction_emojis:
                    return True
            else:
                reaction.remove(user)
                return False

        while True:
            await self.__post_current_page()

            try:
                reaction, user = await self.__context.bot.wait_for('reaction_add', timeout=60.0, check=option_selection_check)
            except asyncio.TimeoutError:
                await self.__message.delete()
                return False, {}
            else:
                emoji = str(reaction.emoji)
                if emoji == emojis.page_next:
                    await reaction.remove(user)
                    self.__set_next_page()
                elif emoji == emojis.page_previous:
                    await reaction.remove(user)
                    self.__set_previous_page()
                else:
                    await self.__message.delete()
                    return True, self.__current_options[emoji]


    async def __post_current_page(self) -> None:
        options_display = Paginator.__get_options_display(self.__current_page, self.__short_text_function)
        page_no = f'page {self.__current_page_no}/{len(self.__pages)}'
        content = f'{self.__title}```{options_display}```{page_no}'
        if self.__message:
            await Paginator.__edit_message(self.__message, self.__context.bot.user, content, list(self.__current_options.keys()), self.__base_reaction_emojis)
        else:
            self.__message = await self.__context.send(content)
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
        self.__current_options = Paginator.__get_options(page)


    def __set_previous_page(self) -> None:
        new_page, new_page_no = Paginator.__get_previous_page(self.__pages, self.__current_page_no)
        self.__set_page(new_page)
        self.__current_page_no = new_page_no


    @staticmethod
    async def __edit_message(message: discord.Message, bot_user: discord.User, content: str, available_reaction_emojis: List[str], base_reaction_emojis: List[str]) -> None:
        valid_emojis = available_reaction_emojis + base_reaction_emojis
        await message.edit(content=content)
        existing_reaction_emojis = [reaction.emoji for reaction in message.reactions]
        reactions_to_remove = []
        reactions_to_add = []
        for reaction in message.reactions:
            if reaction.emoji not in valid_emojis:
                reactions_to_remove.append(reaction)
        for emoji in available_reaction_emojis:
            if emoji not in existing_reaction_emojis:
                reactions_to_add.append(emoji)
        for reaction in reactions_to_remove:
            await reaction.remove(bot_user)
        for emoji in reactions_to_add:
            await message.add_reaction(emoji)


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
    def __get_options(current_page: List[dict]) -> Dict[str, dict]:
        result = {}
        for i, option in enumerate(current_page):
            emoji = emojis.options[i]
            result[emoji] = option
        return result


    @staticmethod
    def __get_options_display(entity_infos: List[dict], short_text_function: Callable[[dict], str]) -> str:
        options = []
        for i, entity_info in enumerate(entity_infos):
            number = str(i + 1)
            short_text = short_text_function(entity_info)
            option = f'{number.rjust(2)} - {short_text}'
            options.append(option)
        return '\n'.join(options)



    @staticmethod
    def __get_previous_page(pages: List[List[dict]], current_page_no: int) -> (List[dict], int):
        if pages:
            if current_page_no > 1:
                current_page_no += 1
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
