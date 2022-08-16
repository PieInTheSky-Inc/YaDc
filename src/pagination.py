import inspect
import math
from typing import Awaitable, Callable, Dict, List, Optional, Tuple, Union

import asyncio
from discord import ApplicationContext, ChannelType, Embed, Message, Reaction, User
from discord.ext.commands import Context

from .pss_entity import EntityDetails
from . import emojis
from . import utils
from .typehints import EntityInfo


# ---------- Typehint definitions ----------

PaginatorOption = Union[EntityDetails, EntityInfo]





# ---------- Classes ----------

class Paginator():
    def __init__(self, ctx: Context, search_term: str, available_options: List[PaginatorOption], short_text_function: Callable[[PaginatorOption], Union[str, Awaitable[str]]], use_pagination: bool, page_size: int = 5, timeout: float = 60.0) -> None:
        self.__context: Context = ctx
        self.__search_term: str = search_term
        self.__available_options: List[PaginatorOption] = list(available_options)
        self.__short_text_function: Callable[[PaginatorOption], Union[str, Awaitable[str]]] = short_text_function
        self.__retrieve_short_text_async: bool = inspect.iscoroutinefunction(short_text_function)
        self.__page_size: int = page_size
        self.__timeout: int = timeout
        self.__use_emojis: bool = None

        self.__is_dm_channel = ctx.channel.type == ChannelType.private
        if ctx.channel.type == ChannelType.text and ctx.guild and ctx.guild.id:
            bot_permissions = ctx.channel.permissions_for(ctx.me)
            if bot_permissions.add_reactions:
                self.__use_emojis = use_pagination
            else:
                self.__use_emojis = False
        else:
            self.__use_emojis = not self.__is_dm_channel

        if not self.__use_emojis:
            self.__page_size = len(self.__available_options)
            self.__base_reaction_emojis = []

        self.__pages: List[List[PaginatorOption]] = Paginator.__get_pages(self.__available_options, self.__page_size)
        self.__page_count: int = len(self.__pages)
        self.__current_page: list = []
        self.__current_page_no: int = 0
        self.__current_options: Dict[str, PaginatorOption] = {}
        self.__set_first_page()
        self.__message: Message = None
        self.__title: str = Paginator.__get_title(search_term)
        self.__base_reaction_emojis: List[str] = []
        if self.__use_emojis:
            self.__base_reaction_emojis = Paginator.__get_base_reaction_emojis(self.__pages)



    async def wait_for_option_selection(self) -> Tuple[bool, Dict]:
        def emoji_selection_check(reaction: Reaction, user: User) -> bool:
            if user != self.__context.bot.user:
                emoji = str(reaction.emoji)
                if (emoji in self.__current_options.keys() or emoji in self.__base_reaction_emojis) and self.__message.id == reaction.message.id:
                    return True
            return False

        def option_selection_check(message: Message) -> bool:
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
            reply: Message = None

            try:
                if self.__use_emojis:
                    reaction, user = await self.__context.bot.wait_for('reaction_add', timeout=self.__timeout, check=emoji_selection_check)
                else:
                    reply = await self.__context.bot.wait_for('message', timeout=self.__timeout, check=option_selection_check)
            except asyncio.TimeoutError:
                await self.__try_delete_message()
                return False, {}
            else:
                if reaction and user:
                    if user != self.__context.author:
                        await utils.discord.try_remove_reaction(reaction, user)
                        repost_page = False
                    else:
                        emoji = str(reaction.emoji)
                        if emoji == emojis.page_next:
                            await utils.discord.try_remove_reaction(reaction, user)
                            self.__set_next_page()
                        elif emoji == emojis.page_previous:
                            await utils.discord.try_remove_reaction(reaction, user)
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
                            await utils.discord.try_delete_message(reply)
                            await self.__try_delete_message()
                            return True, self.__current_options[selection]


    async def __post_current_page(self) -> None:
        options_display = await Paginator.__get_options_display(self.__current_page, self.__short_text_function, self.__retrieve_short_text_async)
        if self.__page_count > 1:
            page_no = f'page {self.__current_page_no}/{self.__page_count}'
        else:
            page_no = ''
        content = f'{self.__title}```{options_display}```{page_no}'
        if self.__message:
            if self.__page_count > 1:
                await self.__message.edit(content=content)
        else:
            self.__message = await utils.discord.reply_with_output(self.__context, [content])
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


    def __set_page(self, page: List[PaginatorOption]) -> None:
        self.__current_page = page
        self.__current_options = Paginator.__get_options(page, self.__use_emojis)


    def __set_previous_page(self) -> None:
        new_page, new_page_no = Paginator.__get_previous_page(self.__pages, self.__current_page_no)
        self.__set_page(new_page)
        self.__current_page_no = new_page_no


    async def __try_delete_message(self) -> bool:
        result = await utils.discord.try_delete_message(self.__message)
        if result:
            self.__message = None
        return result


    @staticmethod
    def __get_base_reaction_emojis(pages: List[List[PaginatorOption]]) -> List[str]:
        if pages and len(pages) > 1:
            return [emojis.page_previous, emojis.page_next]
        else:
            return []


    @staticmethod
    def __get_first_page(pages: List[List[PaginatorOption]]) -> Tuple[List[PaginatorOption], int]:
        if pages:
            return pages[0], 1
        else:
            return [], 0


    @staticmethod
    def __get_next_page(pages: List[List[PaginatorOption]], current_page_no: int) -> Tuple[List[PaginatorOption], int]:
        if pages:
            if len(pages) > current_page_no:
                current_page_no += 1
            else:
                current_page_no = 1
            return pages[current_page_no - 1], current_page_no
        else:
            return [], 0


    @staticmethod
    def __get_pages(available_options: List[PaginatorOption], page_size: int) -> List[List[PaginatorOption]]:
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
    def __get_options(current_page: List[PaginatorOption], use_emojis: bool) -> Dict[str, PaginatorOption]:
        result = {}
        for i, option in enumerate(current_page):
            if use_emojis:
                emoji = emojis.options[i]
                result[emoji] = option
            else:
                result[i + 1] = option
        return result


    @staticmethod
    async def __get_options_display(entity_infos: List[PaginatorOption], short_text_function: Callable[[PaginatorOption], Union[str, Awaitable[str]]], retrieve_short_text_async: bool) -> str:
        options = []
        for i, entity_info in enumerate(entity_infos, 1):
            number = str(i)
            if retrieve_short_text_async:
                short_text = await short_text_function(entity_info)
            else:
                short_text = short_text_function(entity_info)
            option = f'{number.rjust(2)}: {short_text}'
            options.append(option)
        return '\n'.join(options)



    @staticmethod
    def __get_previous_page(pages: List[List[PaginatorOption]], current_page_no: int) -> Tuple[List[PaginatorOption], int]:
        if pages:
            if current_page_no > 1:
                current_page_no -= 1
            else:
                current_page_no = len(pages)
            return pages[current_page_no - 1], current_page_no
        else:
            return [], 0


    @staticmethod
    def __get_title(search_term: str) -> str:
        result = 'Multiple matches found'
        if search_term:
            result += f' while searching for **{search_term}**'
        result += ':'
        return result





from discord import Interaction, MessageInteraction, SelectOption
from discord.ui import View, Select


class OptionSelect(Select):
    def __init__(self,
        title: str,
        options: List[SelectOption]
    ):
        super().__init__(
            min_values=1,
            max_values=1,
            placeholder=title,
            options=options
        )


class ViewBase(View):
    def __init__(self,
        ctx: ApplicationContext,
        *args,
        timeout: float = 60.0,
        **kwargs
    ):
        super().__init__(*args, timeout=timeout, **kwargs)
        self.__context: ApplicationContext = ctx


    async def on_timeout(self):
        self.disable_all_items()


    async def interaction_check(self, interaction: Interaction) -> bool:
        if interaction.user != self.__context.author:
            await interaction.response.send_message(content='You are not allowed to choose.', ephemeral=True, delete_after=5.0)
            return False
        return True


    async def edit_original_message(self, interaction: Interaction, content: str = None, embeds: List[Embed] = None, remove_view: bool = False) -> Interaction:
        view = None if remove_view else self
        return (await interaction.edit_original_message(content=content, embeds=embeds or [], view=view))


    async def disable_view(self, interaction: Interaction) -> Optional[Interaction]:
        self.disable_all_items()
        if interaction:
            return (await self.edit_original_message(interaction))
        return interaction



class SelectView(ViewBase):
    def __init__(self,
            ctx: ApplicationContext,
            title: str,
            available_options: Dict[str, Tuple[str, EntityInfo]],
            *args,
            timeout: float = 60.0,
            **kwargs
        ):
        super().__init__(ctx, *args, timeout=timeout, **kwargs)
        self.__title: str = title
        self.__available_options: Dict[str, Tuple[str, EntityInfo]] = available_options
        select_options = [SelectOption(label=label, value=entity_id) for entity_id, (label, _) in available_options.items()]
        self.__select: OptionSelect = OptionSelect(title, select_options)
        self.__select.callback = self.__select_callback
        self.add_item(self.__select)
        self.__selected_entity_info: EntityInfo = None

    @property
    def select(self) -> OptionSelect:
        return self.__select

    @property
    def selected_entity_info(self) -> Optional[EntityInfo]:
        return self.__selected_entity_info

    @property
    def title(self) -> str:
        return self.__title


    async def __select_callback(self, interaction: Interaction):
        self.__selected_entity_info = self.__available_options[self.__select.values[0]][1]
        self.disable_all_items()
        await interaction.response.edit_message(view=self)
        self.stop()


    async def wait_for_selection(self, interaction: Interaction) -> EntityInfo:
        await self.edit_original_message(interaction, content='Multiple matches have been found')
        if (await self.wait()): # interaction timed out
            await self.disable_view(interaction)
            return None
        await self.edit_original_message(interaction, content='Player found!', remove_view=True)
        return self.selected_entity_info