#!/usr/bin/env python3
# -*- coding: utf-8, vim: expandtab:ts=4 -*

import re
from os.path import join as os_path_join, dirname as os_path_dirname, abspath as os_path_abspath

from html2tei import parse_date, decompose_listed_subtrees_and_mark_media_descendants, tei_defaultdict

PORTAL_URL_PREFIX = 'https://maszol.ro'

ARTICLE_ROOT_PARAMS_SPEC = [(('div',), {'class': 'main_content'})]
SECTION_DICT = {'kultura': 'Kultúra',
                'belfold': 'Belföld',
                'kulfold': 'Külföld',
                'gazdasag': 'Gazdaság',
                'sport': 'Sport',
                'eletmod': 'Életmód',
                'velemeny': 'Vélemény',
                'videok': 'Videók'}


def get_meta_from_articles_spec(tei_logger, url, bs):
    data = tei_defaultdict()
    data['sch:url'] = url
    date_tag = bs.find('time')
    if date_tag is not None:    # 2021. május 25., kedd, 19:49
        parsed_date = parse_date(date_tag.text.strip(), '%Y. %B %d., %A, %H:%M')
        if parsed_date is not None:
            data['sch:datePublished'] = parsed_date
        else:
            tei_logger.log('WARNING', f'{url}: DATE TEXT FORMAT ERROR!')
    else:
        tei_logger.log('WARNING', f'{url}: DATE TAG NOT FOUND!')
    title_and_tags = bs.find('div', class_='article_title')
    if title_and_tags is not None:
        data['sch:name'] = title_and_tags.find('h1').text.strip()
        tags = [a.text.strip() for a in title_and_tags.find_all('a')]
        if len(tags) > 0:
            data['sch:keywords'] = tags
        else:
            tei_logger.log('DEBUG', f'{url}: TAGS NOT FOUND!')
    else:
        tei_logger.log('WARNING', f'{url}: TITLE AND TAGS NOT FOUND IN URL!')
    author = bs.find('span', class_='author')
    if author is not None:
        data['sch:author'] = author.text.split('/')
    else:
        tei_logger.log('WARNING', f'{url}: AUTHOR TAG NOT FOUND!')
    section = url.split('/')[3]
    if section in SECTION_DICT.keys():
        data['sch:articleSection'] = SECTION_DICT[section]
    else:
        tei_logger.log('WARNING', f'{url}: SECTION TAG NOT FOUND!')
    return data


def excluded_tags_spec(tag):
    return tag


BLOCK_RULES_SPEC = {}
BIGRAM_RULES_SPEC = {}
LINKS_SPEC = {'a', '0_MDESC_a', 'img', '0_MDESC_img', 'iframe', '0_MDESC_iframe', 'blockquote'}
DECOMP = [(('script',), {}), (('div',), {'id': 'abox_paceholder'}),
          (('div',), {'id': 'kapcsolodo_paceholder'}),
          (('div',), {'class': 'article-meta'})]

MEDIA_LIST = []


def decompose_spec(article_dec):
    decompose_listed_subtrees_and_mark_media_descendants(article_dec, DECOMP, MEDIA_LIST)
    return article_dec


BLACKLIST_SPEC = [url.strip() for url in
                  open(os_path_join(os_path_dirname(os_path_abspath(__file__)), 'maszol_BLACKLIST.txt')).readlines()]
# https://maszol.ro/eletmod/124103-koronavirus-a-mar-felepult-paciensek-vereben-lev-antitestekkel-kezelnek-a-sulyos-betegeket
# This HTML contains texts that cannot be validated (as TEI XML string).

MULTIPAGE_URL_END = re.compile(r'^\b$')  # Dummy

LINK_FILTER_SUBSTRINGS_SPEC = re.compile('|'.join(['LINK_FILTER_DUMMY_STRING']))


def next_page_of_article_spec(_):
    return None
