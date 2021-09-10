#!/usr/bin/env python3
# -*- coding: utf-8, vim: expandtab:ts=4 -*

import re

from html2tei import parse_date, BASIC_LINK_ATTRS, decompose_listed_subtrees_and_mark_media_descendants, tei_defaultdict

PORTAL_URL_PREFIX = 'https://dummy.hu'

ARTICLE_ROOT_PARAMS_SPEC = []  # (('tagname',), {'attribute_key': 'attribute_value'})


def get_meta_from_articles_spec(tei_logger, url, bs):
    data = tei_defaultdict()
    data['sch:url'] = url
    write_it = ''
    article_root = bs.find()    # használata opcionális
    data['sch:datePublished'] = write_it
    # else: tei_logger.log('WARNING', f'{url}: DATE FORMAT ERROR!')
    data['sch:dateModified'] = write_it
    # else: tei_logger.log('WARNING', f'{url}: MODIFIED DATE TEXT FORMAT ERROR!')
    data['sch:name'] = write_it
    # else: tei_logger.log('WARNING', f'{url}: TITLE NOT FOUND IN URL!')
    data['sch:author'] = []
    # else: tei_logger.log('WARNING', f'{url}: AUTHOR TAG NOT FOUND!')
    data['sch:articleSection'] = write_it
    # else: tei_logger.log('WARNING', f'{url}: SECTION TAG NOT FOUND!')
    data['sch:keywords'] = []
    # else: tei_logger.log('WARNING', f'{url}: TAGS NOT FOUND!')
    return data
    # tei_logger.log('WARNING', f'{url}: METADATA CONTAINER NOT FOUND!')
    # tei_logger.log('WARNING', f'{url}: ARTICLE BODY NOT FOUND!')
    # return None


def excluded_tags_spec(tag):
    return tag


BLOCK_RULES_SPEC = {}
BIGRAM_RULES_SPEC = {}
LINKS_SPEC = {}
DECOMP = []
MEDIA_LIST = []


def decompose_spec(article_dec):
    decompose_listed_subtrees_and_mark_media_descendants(article_dec, DECOMP, MEDIA_LIST)
    return article_dec


BLACKLIST_SPEC = []
LINK_FILTER_SUBSTRINGS_SPEC = re.compile('|'.join(['LINK_FILTER_DUMMY_STRING']))

MULTIPAGE_URL_END = re.compile(r'^\b$')  # Dummy


def next_page_of_article_spec(_):
    return None
