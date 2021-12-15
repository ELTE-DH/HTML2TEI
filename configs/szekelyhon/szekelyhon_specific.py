#!/usr/bin/env python3
# -*- coding: utf-8, vim: expandtab:ts=4 -*

import re

from html2tei import parse_date, BASIC_LINK_ATTRS, decompose_listed_subtrees_and_mark_media_descendants, tei_defaultdict

PORTAL_URL_PREFIX = 'https://szekelyhon.ro'
ARTICLE_ROOT_PARAMS_SPEC = [(('div',), {'class': 'cikkocka'})]
SECTION_DICT = {'aktualis': 'Aktuális', 'vilag': 'Világ', 'sport': 'Sport', 'magazin': 'Magazin',
                'muvelodes': 'Művelődés', 'faluszerte': 'Faluszerte', 'penna': 'Penna', 'kulfold': 'Külföld'}


def get_meta_from_articles_spec(tei_logger, url, bs):
    data = tei_defaultdict()
    data['sch:url'] = url
    write_it = ''
    for args, kwargs in ARTICLE_ROOT_PARAMS_SPEC:
        article_root = bs.find(*args, **kwargs)
        if article_root is not None:
            break
    else:
        print('WARNING', f'{url} ARTICLE BODY ROOT NOT FOUND!')
        return None

    date_and_author = article_root.find('div', class_='author')
    dates_and_author_parts = [date_part.strip() for date_part in date_and_author.text
                                        .replace('\n\n\t\t\t\t\t\t', '&bullet;').split('&bullet;')]
    if len(dates_and_author_parts) > 0:
        parsed_date = parse_date(dates_and_author_parts[1], '%Y. %B %d., %H:%M')
        if parsed_date is not None:
            data['sch:datePublished'] = parsed_date
        else:
            tei_logger.log('WARNING', f'{url}: DATE FORMAT ERROR!')
            print(parsed_date)
        if len(dates_and_author_parts) > 2 and dates_and_author_parts[2].startswith('utolsó'):
            mod = dates_and_author_parts[2]
            mod = mod[mod.find(': ') + 2:]
            parsed_moddate = parse_date(mod, '%Y. %B %d., %H:%M')
            if parsed_moddate is not None:
                data['sch:dateModified'] = parsed_moddate
    else:
        tei_logger.log('WARNING', f'{url}: DATE TAG NOT FOUND!')
    is_author = dates_and_author_parts[0]
    if is_author != 'Székelyhon':
        data['sch:author'] = [author.strip() for author in is_author.split(',')]
    title = article_root.find('h1')  # , class_='maintitle'
    if title is not None:
        data['sch:name'] = title.text.strip()
    else:
        tei_logger.log('WARNING', f'{url}: TITLE NOT FOUND IN URL!')

    section = url.split('/')[3]
    if section in SECTION_DICT.keys():
        data['sch:articleSection'] = SECTION_DICT[section]
    else:
        tei_logger.log('WARNING', f'{url}: SECTION TAG NOT FOUND!')
    tags = article_root.find('div', class_='tags_con1')
    if tags is not None and len(tags) > 0:
        tags = [tag.text.strip() for tag in tags.find_all('div', class_='tags_item')]
        if len(tags) > 0:
            data['sch:keywords'] = tags
    else:
        tei_logger.log('DEBUG', f'{url}: TAGS NOT FOUND!')
    return data


def excluded_tags_spec(tag):
    return tag


BLOCK_RULES_SPEC = {}
BIGRAM_RULES_SPEC = {'kviz': {('cimsor', 'det_by_any_desc'): ('kviz', 'kerdes')}}
LINKS_SPEC = BASIC_LINK_ATTRS
DECOMP = [(('div',), {'class': 'addblockp'}),
          (('div',), {'class': 'votenew'}),
          (('div',), {'class': 'share_cikk2'}),
          (('h1',), {'class': 'maintitle'}),
          (('div',), {'class': 'tags_con1'}),
          (('div',), {'class': 'author'}),
          (('div',), {'class': 'clear'}),
          (('div',), {'class': 'hide-fulldesktop'}),
          (('h1',), {'class': 'titlefont'})
          ]
MEDIA_LIST = []


def decompose_spec(article_dec):
    decompose_listed_subtrees_and_mark_media_descendants(article_dec, DECOMP, MEDIA_LIST)
    return article_dec


BLACKLIST_SPEC = []

MULTIPAGE_URL_END = re.compile(r'^\b$')  # Dummy

LINK_FILTER_SUBSTRINGS_SPEC = re.compile('|'.join(['LINK_FILTER_DUMMY_STRING']))


def next_page_of_article_spec(_):
    return None
