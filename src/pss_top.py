#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import math

import emojis
import pss_core as core
import pss_tournament as tourney


# ---------- Top 100 Alliances ----------

def get_top_alliances(take: int = 100, as_embed: bool = False):
    path = f'AllianceService/ListAlliancesByRanking?skip=0&take={take}'
    raw_data = core.get_data_from_path(path)
    data = core.xmltree_to_dict3(raw_data, 'AllianceId')
    if as_embed:
        return _get_top_alliances_as_embed(data, take), True
    else:
        return _get_top_alliances_as_text(data, take), True


def _get_top_alliances_as_embed(alliance_data: dict, take: int = 100):
    return ''


def _get_top_alliances_as_text(alliance_data: dict, take: int = 100):
    tourney_running = tourney.is_tourney_running()

    posts = []

    headline = f'**Top {take} alliances**'
    lines = [headline]
    lines.append('')

    trailing_space_count = int(math.log10(take))
    position = 0
    current_post_len = len(headline) + 1
    for entry in alliance_data.values():
        position += 1
        pos_str = str(position).rjust(trailing_space_count)
        name = entry['AllianceName']
        trophies = entry['Trophy']
        stars = entry['Score']

        trophy_txt = f'{trophies} {emojis.trophy}'
        if tourney_running:
            stars_txt = f', {stars} {emojis.star}'
        else:
            stars_txt = ''

        line = f'**{pos_str}.** {name} ({trophy_txt}{stars_txt})'

        current_post_len += len(line) + 1
        if current_post_len > core.MAXIMUM_CHARACTERS:
            posts.append('\n'.join(lines))
            lines = []
            current_post_len = len(line)

        lines.append(line)

    posts.append('\n'.join(lines))
    return posts