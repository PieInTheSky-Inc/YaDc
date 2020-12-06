import datetime
from typing import Callable, Dict, List, Optional, Tuple, Union

from discord import Embed

import pss_assert
import pss_crew as crew
import pss_entity as entity
from pss_exception import Error
import pss_item as item
import pss_lookups as lookups
import pss_research as research
import pss_room as room
import pss_sprites as sprites
import settings
import utils


# ---------- Constants ----------

PROMOTION_DESIGN_BASE_PATH: str = 'PromotionService/ListAllPromotionDesigns2?languageKey=en'
PROMOTION_DESIGN_DESCRIPTION_PROPERTY_NAME: str = 'Name'
PROMOTION_DESIGN_KEY_NAME: str = 'PromotionDesignId'

REWARD_TYPE_GET_ENTITY_FUNCTIONS: Dict[str, Callable] = {
    'item': item.get_item_details_by_id,
    'character': crew.get_char_details_by_id,
    'research': research.get_research_details_by_id,
    'room': room.get_room_details_by_id,
    'starbux': None
}





# ---------- Classes ----------

class LegacyPromotionDesignDetails(entity.LegacyEntityDetails):
    def __init__(self, promotion_info: entity.EntityInfo) -> None:
        """
        RewardString
        """

        self.__name: str = promotion_info.get('Name', None)
        self.__description: str = promotion_info.get('Description', None)
        self.__flags: int = int(promotion_info.get('Flags', '0'))
        self.__requirements: List[PromoRequirement] = __convert_requirement_string(promotion_info.get('RequirementString', ''))
        self.__sprite_id_background: int = int(promotion_info.get('BackgroundSpriteId', '0'))
        self.__sprite_id_button: int = int(promotion_info.get('ButtonSpriteId', '0'))
        self.__sprite_id_close_button: int = int(promotion_info.get('CloseButtonSpriteId', '0'))
        self.__sprite_id_icon: int = int(promotion_info.get('IconSpriteId', '0'))
        self.__sprite_id_title: int = int(promotion_info.get('TitleSpriteId', '0'))
        self.__subtitle: str = promotion_info.get('Subtitle', None)
        self.__vip_extra_crew_draws: int = int(promotion_info('ExtraCrewDraws', '0'))
        self.__vip_resource_conversion_discount: int = int(promotion_info('ResourceConversionDiscountPercentage', '0'))
        self.__vip_reward_store_discount: int = int(promotion_info('RewardStoreDiscountPercentage', '0'))
        self.__vip_speed_up_discount: int = int(promotion_info('SpeedUpDiscountPercentage', '0'))
        self.__vip_starbux_bonus: int = int(promotion_info.get('StarbuxBonusPercentage', '0'))
        self.__vip_xp_bonus: int = int(promotion_info.get('XPBonusPercentage', '0'))

        self.__from_datetime: datetime.datetime = __get_datetime(promotion_info.get('FromDate', None), settings.API_DATETIME_FORMAT_CUSTOM)
        self.__to_datetime: datetime.datetime = __get_datetime(promotion_info.get('ToDate', None), settings.API_DATETIME_FORMAT_CUSTOM)
        self.__iap_options: str = utils.convert.iap_options_mask(promotion_info.get('PurchaseMask', '0'))

        details_long: List[Tuple[str, str]] = [
        ]
        details_short: List[Tuple[str, str, bool]] = [
        ]

        super().__init__(
            name=promotion_info[PROMOTION_DESIGN_DESCRIPTION_PROPERTY_NAME],
            description=promotion_info['Description'],
            details_long=details_long,
            details_short=details_short
        )


    @property
    def description(self) -> str:
        return self.__description

    @property
    def from_datetime(self) -> datetime.datetime:
        return self.__from_datetime

    @property
    def iap_options(self) -> str:
        return self.__iap_options

    @property
    def name(self) -> str:
        return self.__name

    @property
    def requirements(self) -> str:
        pretty_requirements = [requirement.get_pretty_requirement_string() for requirement in self.__requirements]
        return ', '.join(pretty_requirements)

    @property
    def sprite_url_background(self) -> str:
        return sprites.get_sprite_download_url(self.__sprite_id_background)

    @property
    def sprite_url_button(self) -> str:
        return sprites.get_sprite_download_url(self.__sprite_id_button)

    @property
    def sprite_url_close_button(self) -> str:
        return sprites.get_sprite_download_url(self.__sprite_id_close_button)

    @property
    def sprite_url_icon(self) -> str:
        return sprites.get_sprite_download_url(self.__sprite_id_icon)

    @property
    def sprite_url_title(self) -> str:
        return sprites.get_sprite_download_url(self.__sprite_id_title)

    @property
    def subtitle(self) -> str:
        return self.__subtitle

    @property
    def to_datetime(self) -> datetime.datetime:
        return self.__to_datetime

    @property
    def vip_extra_crew_draws(self) -> int:
        return self.__vip_extra_crew_draws

    @property
    def vip_resource_conversion_discount(self) -> int:
        """Represents a percentage."""
        return self.__vip_resource_conversion_discount

    @property
    def vip_reward_store_discount(self) -> int:
        """Represents a percentage."""
        return self.__vip_reward_store_discount

    @property
    def vip_speed_up_discount(self) -> int:
        """Represents a percentage."""
        return self.__vip_speed_up_discount

    @property
    def vip_starbux_bonus(self) -> int:
        """Represents a percentage."""
        return self.__vip_starbux_bonus

    @property
    def vip_xp_bonus(self) -> int:
        """Represents a percentage."""
        return self.__vip_xp_bonus





class PromoRequirement():
    def __init__(self, requirement: str) -> None:
        self.__lower_than: bool = False
        self.__greater_than: bool = False
        self.__equal: bool = False
        self.__requirement_type: str = None
        self.__requirement_value: int = None

        requirement = requirement.strip()
        if '>' in requirement:
            self.__greater_than = True
            if '>=' in requirement:
                self.__requirement_type, self.__requirement_value = __get_requirement_type_and_value(requirement, '>=')
            else:
                self.__requirement_type, self.__requirement_value = __get_requirement_type_and_value(requirement, '>', 1)
        elif '<' in requirement:
            self.__lower_than = True
            if '<=' in requirement:
                self.__requirement_type, self.__requirement_value = __get_requirement_type_and_value(requirement, '<=')
            else:
                self.__requirement_type, self.__requirement_value = __get_requirement_type_and_value(requirement, '<', -1)
        elif '==' in requirement:
            self.__equal = True
            self.__requirement_type, self.__requirement_value = __get_requirement_type_and_value(requirement, '==')


    def get_pretty_requirement_string(self) -> str:
        modifier = 'Min' if self.__greater_than else 'Max' if self.__lower_than else ''
        if modifier:
            modifier = f'{modifier} '
        pretty_requirement_type = __get_pretty_requirement_type(self.__requirement_type)
        result = f'{modifier}{pretty_requirement_type}: {self.__requirement_value}'
        return result





# ---------- Promo info ----------

async def get_promotion_details_by_id(promotion_design_id: str, promotions_data: dict = None) -> LegacyPromotionDesignDetails:
    if promotion_design_id:
        if promotions_data is None:
            promotions_data = await promotion_designs_retriever.get_data_dict3()

        if promotion_design_id and promotion_design_id in promotions_data.keys():
            promotion_info = promotions_data[promotion_design_id]
            promotion_details = LegacyPromotionDesignDetails(promotion_info)
            return promotion_details

    return None


def get_promotions_details_by_name(promotion_name: str) -> entity.EntityDetailsCollection:
    pss_assert.valid_entity_name(promotion_name, 'promotion_name')
    raise NotImplemented()


async def get_promotions_infos_by_name(promotion_name: str, as_embed: bool = settings.USE_EMBEDS) -> Union[List[Embed], List[str]]:
    pss_assert.valid_entity_name(promotion_name, 'promotion_name')

    promotion_infos = await promotion_designs_retriever.get_entities_infos_by_name(promotion_name)
    promotions_details = [LegacyPromotionDesignDetails(promotion_info) for promotion_info in promotion_infos if promotion_info['PromotionType'] == 'FirstPurchase']

    if not promotions_details:
        raise Error(f'Could not find a promotion named `{promotion_name}`.')
    else:
        if as_embed:
            return _get_promotions_details_as_embed(promotions_details)
        else:
            return _get_promotions_details_as_text(promotion_name, promotions_details)


def _get_promotions_details_as_embed(promotion_details: Dict[str, dict]) -> Embed:
    pass


def _get_promotions_details_as_text(promotion_name: str, promotion_details: Dict[str, dict]) -> List[str]:
    promotion_details_count = len(promotion_details)

    lines = [f'Promotion stats for **{promotion_name}**']
    for i, promotion_details in enumerate(promotion_details):
        if promotion_details_count > 2:
            lines.extend(promotion_details.get_details_as_text_short())
        else:
            lines.extend(promotion_details.get_details_as_text_long())
            if i < promotion_details_count - 1:
                lines.append(utils.discord.EMPTY_LINE)

    return lines





# ---------- Transformation functions ----------





# ---------- Helper functions ----------

def __convert_reward_string(reward_string: str) -> Dict[str, str]:
    result = {}

    if not reward_string:
        return result

    for reward in reward_string.split('|'):
        reward_type, entity_id = reward.split(':')
        result.setdefault(reward_type, []).append(entity_id)

    return result


def __convert_requirement_string(requirement_string: str) -> List[PromoRequirement]:
    result: List[PromoRequirement] = []

    if not requirement_string:
        return result

    for requirement in requirement_string.split('&&'):
        promo_requirement = PromoRequirement(requirement)
        result.append(promo_requirement)

    return result


def __get_datetime(api_datetime: str, datetime_format: str) -> datetime.datetime:
    if not api_datetime:
        return None
    result = datetime.datetime.strptime(api_datetime, datetime_format)
    if result < settings.PSS_START_DATE:
        return None
    else:
        return result


def __get_pretty_requirement_type(requirement_type: str, language_key: str = 'en') -> Optional[str]:
    if language_key and requirement_type:
        result = lookups.PROMO_REQUIREMENT_TYPE_LOOKUP.get(language_key, {}).get(requirement_type, None)
        return result
    else:
        return None


def __get_pretty_reward_string(rewards: Dict[str, List[str]]) -> str:
    result = []

    for entity_type in [key for key in rewards.keys() if rewards[key]]:
        get_entity_details_function = REWARD_TYPE_GET_ENTITY_FUNCTIONS[entity_type.lower()]
        if get_entity_details_function:
            intermediate = []
            for entity_id in rewards[entity_type]:
                entity_details: entity.LegacyEntityDetails = get_entity_details_function(entity_id)
                intermediate.append(entity_details.get_details_as_text_short())
            result.append(', '.join(intermediate))
        else:
            result.append(f'{entity_type}: {sum(rewards[entity_type])}')

    return ', '.join(result)


def __get_requirement_type_and_value(requirement_string: str, separator: str, add_to_value: int = 0) -> Tuple[str, int]:
    requirement_type, requirement_value = requirement_string.split(separator)
    requirement_value = int(requirement_value) + add_to_value
    return requirement_type, requirement_value





# ---------- Create EntityDetails ----------





# ---------- Initilization ----------

promotion_designs_retriever = entity.EntityRetriever(
    PROMOTION_DESIGN_BASE_PATH,
    PROMOTION_DESIGN_KEY_NAME,
    PROMOTION_DESIGN_DESCRIPTION_PROPERTY_NAME,
    cache_name='PromotionDesigns'
)