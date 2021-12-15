#!/usr/bin/env python3
# -*- coding: utf-8, vim: expandtab:ts=4 -*

import re
from os.path import join as os_path_join, dirname as os_path_dirname, abspath as os_path_abspath

from html2tei import parse_date, BASIC_LINK_ATTRS, decompose_listed_subtrees_and_mark_media_descendants, tei_defaultdict

PORTAL_URL_PREFIX = 'https://termvil.hu'

ARTICLE_ROOT_PARAMS_SPEC = [(('div',), {'class': 'btArticleContentInnerInner'})]


def get_meta_from_articles_spec(tei_logger, url, bs):
    data = tei_defaultdict()
    data['sch:url'] = url
    if bs.find('article'):
        date_tag = bs.find('meta', {'property': 'article:published_time'})
        if date_tag is not None and 'content' in date_tag.attrs.keys():
            parsed_date = parse_date(date_tag.attrs['content'][:19], '%Y-%m-%dT%H:%M:%S')
            data['sch:datePublished'] = parsed_date
        else:
            print('WARNING', f'{url}: DATE TAG NOT FOUND!')
        date_mod_tag = bs.find('meta', {'property': 'article:modified_time'})
        if date_mod_tag is not None and 'content' in date_tag.attrs.keys():
            parsed_mod_date = parse_date(date_mod_tag.attrs['content'][:19], '%Y-%m-%dT%H:%M:%S')
            data['sch:dateModified'] = parsed_mod_date
        title_root = bs.find('h1')
        if title_root:
            title = title_root.find('span', class_='bt_bb_headline_content')
            if title is not None:
                data['sch:name'] = title.text.strip()
            else:
                tei_logger.log('WARNING', f'{url}: TITLE NOT FOUND IN URL!')
            section = title_root.find('span', class_='bt_bb_headline_superheadline')
            if section is not None:
                data['sch:articleSection'] = section.text.strip()
            else:
                tei_logger.log('WARNING', f'{url}: SECTION TAG NOT FOUND!')
        keywords_root = bs.find('div', class_='btTagsRow')
        if keywords_root:
            keywords = [kw.text.strip() for kw in keywords_root.find_all('a', {'href': True})]
            if len(keywords) > 0:
                data['sch:keywords'] = keywords
        else:
            tei_logger.log('WARNING', f'{url}: TAGS NOT FOUND!')
        return data
    else:
        tei_logger.log('WARNING', f'{url}: ARTICLE BODY NOT FOUND!')
        return None


def excluded_tags_spec(tag):
    return tag


BLOCK_RULES_SPEC = {}
BIGRAM_RULES_SPEC = {}
LINKS_SPEC = BASIC_LINK_ATTRS
DECOMP = []
MEDIA_LIST = [(('div',), {'class': 'gallery'})]

LINK_FILTER_SUBSTRINGS_SPEC = re.compile('|'.join(['LINK_FILTER_DUMMY_STRING']))


def decompose_spec(article_dec):
    decompose_listed_subtrees_and_mark_media_descendants(article_dec, DECOMP, MEDIA_LIST)
    return article_dec


BLACKLIST_SPEC = [url.strip() for url in
                  open(os_path_join(os_path_dirname(os_path_abspath(__file__)), 'termvil_BLACKLIST.txt')).readlines()]

MULTIPAGE_URL_END = re.compile(r'^\b$')  # Dummy


def next_page_of_article_spec(_):
    return None
