#!/usr/bin/env python3
# -*- coding: utf-8, vim: expandtab:ts=4 -*
import json
import re

from src.html2tei import parse_date, BASIC_LINK_ATTRS, decompose_listed_subtrees_and_mark_media_descendants, tei_defaultdict
from src.html2tei import json_to_html

PORTAL_URL_PREFIX = 'https://nepszava.hu'

ARTICLE_ROOT_PARAMS_SPEC = [(('article_body_root',), {})]


def get_meta_from_articles_spec(tei_logger, url, bs):
    data = tei_defaultdict()
    data['sch:url'] = url
    raw_meta = bs.find('json_article').text
    json_meta = json.loads(raw_meta)
    title = json_meta['title']
    pub_date = json_meta['public_date']
    column = [rov['cim'] for rov in json_meta['rovat']]
    authors = [rov['nev'] for rov in json_meta['authors'] if type(rov['nev']) is str]
    keywords = [rov['cim'] for rov in json_meta['tags']]
    if len(title) > 0:
        data['sch:name'] = title
    if len(authors) > 0:
        data['sch:author'] = authors
    main_col = column[0]
    [keywords.append(col) for col in column if col != main_col]
    data['sch:articleSection'] = main_col
    if len(keywords) > 0:
        data['sch:keywords'] = keywords
    if pub_date is not None:
        parsed_pub_date = parse_date(pub_date, '%Y.%m.%d. %H:%M')  # 2020.10.13. 12:37
        if parsed_pub_date is not None:
            data['sch:datePublished'] = parsed_pub_date
        else:
            tei_logger.log('WARNING', f'{url}: DATE FORMAT ERROR!')
    if bs.find('xml') is not None:
        tei_logger.log('WARNING', f'{url}: XML fragment!')
        return None
    return data


def excluded_tags_spec(tag):
    return tag


BLOCK_RULES_SPEC = {}
BIGRAM_RULES_SPEC = {}
LINKS_SPEC = BASIC_LINK_ATTRS
DECOMP = []
MEDIA_LIST = []


def decompose_spec(article_dec):
    decompose_listed_subtrees_and_mark_media_descendants(article_dec, DECOMP, MEDIA_LIST)
    return article_dec


BLACKLIST_SPEC = ['https://nepszava.hu/json/cikk.json?id=1029976_felpalyas-utzar-a-budakeszi-uton',
                  'https://nepszava.hu/json/cikk.json?id=1029970_emelkedtek-az-indexek-europaban',
                  'https://nepszava.hu/json/cikk.json?id=1029966_reumatapaszra-csaptak-le-a-vamosok']
LINK_FILTER_SUBSTRINGS_SPEC = re.compile('|'.join(['LINK_FILTER_DUMMY_STRING']))

MULTIPAGE_URL_END = re.compile(r'^\b$')  # Dummy


def next_page_of_article_spec(_):
    return None


def transform_to_html(url, raw_html, warc_logger):
    _ = url, warc_logger
    return json_to_html(url, raw_html, warc_logger)
