#!/usr/bin/env python3
# -*- coding: utf-8, vim: expandtab:ts=4 -*

import re

from html2tei import parse_date, BASIC_LINK_ATTRS, decompose_listed_subtrees_and_mark_media_descendants, tei_defaultdict

PORTAL_URL_PREFIX = 'https://utazomajom.hu'

ARTICLE_ROOT_PARAMS_SPEC = [(('div',), {'class': 'content'})]


def get_meta_from_articles_spec(tei_logger, url, bs):
    data = tei_defaultdict()
    data['sch:url'] = url
    article_root = bs.find('article', class_=False)
    if not article_root:
        tei_logger.log('WARNING', f'{url}: ARTICLE BODY NOT FOUND!')
        return None
    header = article_root.find('header')
    if header is None:
        tei_logger.log('WARNING', f'{url}: HEADER TAG NOT FOUND!')
    else:
        pub_date = header.find('time')
        if pub_date:    # 2021. augusztus 10. kedd - 16:59
            parsed_date = parse_date(pub_date.text.strip(), '%Y. %B %d. %A - %H:%M')
            if parsed_date:
                data['sch:datePublished'] = parsed_date
            else:
                tei_logger.log('WARNING', f'{url}: DATE FORMAT ERROR!')
        else:
            tei_logger.log('WARNING', f'{url}: DATE NOT FOUND IN URL!')

        title_tag = header.find('h1', class_='typo-h1')
        if title_tag:
            data['sch:name'] = title_tag.text.strip()
        else:
            tei_logger.log('WARNING', f'{url}: TITLE NOT FOUND IN URL!')
        author_tag = header.find('span', class_='typo-weight-bold')
        if author_tag:
            data['sch:author'] = [author_tag.text.strip()]
            if ' ' in data['sch:author'] or ',' in data['sch:author'] or \
                    len(header.find('span', class_='typo-weight-bold')) > 1:
                print(url, author_tag)
        else:
            tei_logger.log('WARNING', f'{url}: AUTHOR TAG NOT FOUND!')
    data['sch:articleSection'] = 'Élménybeszámolók'
    keyword_root = bs.find('div', class_='my-5')
    if keyword_root:
        data['sch:keywords'] = [a.text.strip() for a in keyword_root.find_all('a', class_='button')]
    else:
        tei_logger.log('WARNING', f'{url}: TAGS NOT FOUND!')
    return data


def excluded_tags_spec(tag):
    return tag


BLOCK_RULES_SPEC = {}
BIGRAM_RULES_SPEC = {}
LINKS_SPEC = BASIC_LINK_ATTRS
DECOMP = [(('div',), {'class': 'um_widget_bsimple'}),
          (('span',), {'class': 'js-suggestsimilar-trigger'}),
          (('nav',), {'class': 'suggestSimilar'}),
          (('noscript',), {}), (('script',), {})
          ]
MEDIA_LIST = []


def decompose_spec(article_dec):
    decompose_listed_subtrees_and_mark_media_descendants(article_dec, DECOMP, MEDIA_LIST)
    return article_dec


BLACKLIST_SPEC = []

LINK_FILTER_SUBSTRINGS_SPEC = re.compile('|'.join(['LINK_FILTER_DUMMY_STRING']))

MULTIPAGE_URL_END = re.compile(r'^\b$')  # Dummy


def next_page_of_article_spec(_):
    return None

