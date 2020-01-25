#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import discord
import os
from typing import Dict, List, Set, Tuple

from cache import PssCache
import emojis
import pss_assert
import pss_entity as entity
import pss_core as core
import pss_lookups as lookups
import settings
import utility as util


# ---------- Constants ----------

PROMOTION_DESIGN_BASE_PATH = 'PromotionService/ListAllPromotionDesigns2?languageKey=en'
PROMOTION_DESIGN_KEY_NAME = 'PromotionDesignId'
PROMOTION_DESIGN_DESCRIPTION_PROPERTY_NAME = 'Name'










# ---------- Initilization ----------










# ---------- Classes ----------

class PromotionDesignDetails(entity.EntityDesignDetails):
    def __init__(self, promotion_design_info: dict):
        """
        FromDate ('01.01.00 00:00' is None)
        ToDate('01.01.00 00:00' is None)
        RequirementString
        PurchaseMask
        Name
        Description
        IconSpriteId(for embeds)
        BackgroundSpriteId(for embeds)
        TitleSpriteId(for embeds)
        ButtonSpriteId(for embeds)
        CloseButtonSpriteId(for embeds)
        Flags
        RewardString
        ResourceConversionDiscountPercentage(for VIP)
        RewardStoreDiscountPercentage(for VIP)
        SpeedUpDiscountPercentage(for VIP)
        ExtraCrewDraws(for VIP)
        StarbuxBpnusPercentage(for VIP)
        SubTitle
        XPBonusPercentage
        """

        details_long: List[Tuple[str, str]] = [
        ]
        details_short: List[Tuple[str, str, bool]] = [
        ]

        super().__init__(
            name=promotion_design_info[PROMOTION_DESIGN_DESCRIPTION_PROPERTY_NAME],
            description=promotion_design_info['Description'],
            details_long=details_long,
            details_short=details_short
        )


    @property
    def ability(self) -> str:
        pass










# ---------- Helper functions ----------










# ---------- Crew info ----------

def get_promotion_design_details_by_id(promotion_design_id: str, promotions_designs_data: dict = None) -> PromotionDesignDetails:
    if promotion_design_id:
        if promotions_designs_data is None:
            promotions_designs_data = promotion_designs_retriever.get_data_dict3()

        if promotion_design_id and promotion_design_id in promotions_designs_data.keys():
            promotion_design_info = promotions_designs_data[promotion_design_id]
            promotion_design_details = PromotionDesignDetails(promotion_design_info)
            return promotion_design_details

    return None


def get_promotion_design_details_by_name(promotion_name: str, as_embed: bool = settings.USE_EMBEDS):
    pss_assert.valid_entity_name(promotion_name, 'promotion_name')

    promotion_design_infos = promotion_designs_retriever.get_entity_design_infos_by_name(promotion_name)
    promotions_designs_details = [PromotionDesignDetails(promotion_design_info) for promotion_design_info in promotion_design_infos if promotion_design_info['PromotionType'] == 'FirstPurchase']

    if not promotions_designs_details:
        return [f'Could not find a promotion named **{promotion_name}**.'], False
    else:
        if as_embed:
            return _get_promotions_details_as_embed(promotions_designs_details), True
        else:
            return _get_promotions_details_as_text(promotion_name, promotions_designs_details), True


def _get_promotions_details_as_embed(promotion_design_details: Dict[str, dict]) -> discord.Embed:
    pass


def _get_promotions_details_as_text(promotion_name: str, promotion_design_details: Dict[str, dict]) -> List[str]:
    promotion_details_count = len(promotion_design_details)

    lines = [f'Promotion stats for **{promotion_name}**']
    for i, promotion_details in enumerate(promotion_design_details):
        if promotion_details_count > 2:
            lines.extend(promotion_details.get_details_as_text_short())
        else:
            lines.extend(promotion_details.get_details_as_text_long())
            if i < promotion_details_count - 1:
                lines.append(settings.EMPTY_LINE)

    return lines




















# ---------- Initilization ----------

promotion_designs_retriever = entity.EntityDesignsRetriever(
    PROMOTION_DESIGN_BASE_PATH,
    PROMOTION_DESIGN_KEY_NAME,
    PROMOTION_DESIGN_DESCRIPTION_PROPERTY_NAME,
    cache_name='PromotionDesigns'
)











# ---------- Testing ----------

if __name__ == '__main__':
    test_promotions = ['alpaco']
    for promotion_name in test_promotions:
        os.system('clear')
        result = get_promotion_design_details_by_name(promotion_name, as_embed=False)
        for line in result[0]:
            print(line)
        print('')
        result = ''
