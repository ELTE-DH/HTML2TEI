#!/usr/bin/env python3
# -*- coding: utf-8, vim: expandtab:ts=4 -*-

import re

from html2tei import parse_date, BASIC_LINK_ATTRS, decompose_listed_subtrees_and_mark_media_descendants, tei_defaultdict

PORTAL_URL_PREFIX = 'https://www.nnk.gov.hu'

ARTICLE_ROOT_PARAMS_SPEC = [(('div',), {'itemprop': 'articleBody'})]


def get_meta_from_articles_spec(tei_logger, url, bs):
    data = tei_defaultdict()
    data['sch:url'] = url
    date_tags = bs.find_all('time')  # <time datetime="2020-12-23T14:13:31+01:00" itemprop="datePublished">
    if len(date_tags) > 0:
        for date in date_tags:
            if date.get('datetime'):
                parsed_date = parse_date(date.attrs['datetime'][:19], '%Y-%m-%dT%H:%M:%S')
                if date.get('itemprop') == 'datePublished':
                    data['sch:datePublished'] = parsed_date
                elif date.get('itemprop') == 'dateModified':
                    data['sch:dateModified'] = parsed_date
    else:
        tei_logger.log('WARNING', f'{url}: DATE TAG NOT FOUND ERROR!')

    title = bs.find('h2', itemprop='headline')
    if title:
        data['sch:name'] = title.text
    else:
        tei_logger.log('WARNING', f'{url}: TITLE NOT FOUND IN URL!')
    return data


def excluded_tags_spec(tag):
    return tag


def portal_spec_fun(article):
    return article


BLOCK_RULES_SPEC = {}
BIGRAM_RULES_SPEC = {'melleklet': {('table_text', 'det_by_any_desc'): ('bekezdes', 'to_unwrap')},
                     'bekezdes': {('media_hivatkozas', 'det_by_any_child'): ('media_tartalom', 'media_hivatkozas')}}

LINKS_SPEC = BASIC_LINK_ATTRS
DECOMP = [(('script',), {})]
MEDIA_LIST = []


def decompose_spec(article_dec):
    decompose_listed_subtrees_and_mark_media_descendants(article_dec, DECOMP, MEDIA_LIST)
    for d in article_dec.find_all('span'):
        if 'JavaScript' in d.text.strip():
            d.decompose()
    return article_dec


BLACKLIST_SPEC = []

MULTIPAGE_URL_END = re.compile(r'^\b$')  # Dummy


def next_page_of_article_spec(_):
    return None
