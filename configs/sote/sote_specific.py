#!/usr/bin/env python3
# -*- coding: utf-8, vim: expandtab:ts=4 -*

import re

from html2tei import parse_date, BASIC_LINK_ATTRS, decompose_listed_subtrees_and_mark_media_descendants, tei_defaultdict

PORTAL_URL_PREFIX = 'https://semmelweis.hu'

ARTICLE_ROOT_PARAMS_SPEC = [(('article',), {})]


def get_meta_from_articles_spec(tei_logger, url, bs):
    data = tei_defaultdict()
    data['sch:url'] = url
    if bs.find('article'):
        date_tag = bs.find('time')  # <time class="updated" datetime="2019-12-27T13:31:40+01:00">
        if date_tag is not None and 'datetime' in date_tag.attrs.keys():
            parsed_date = parse_date(date_tag.attrs['datetime'][:19], '%Y-%m-%dT%H:%M:%S')
            data['sch:datePublished'] = parsed_date
        else:
            tei_logger.log('WARNING', f'{url}: DATE FORMAT ERROR!')
        title = bs.find('h1', class_='entry-title')
        if title is not None:
            data['sch:name'] = title.text.strip()
        else:
            tei_logger.log('WARNING', f'{url}: TITLE NOT FOUND IN URL!')

        section_line = bs.find('div', class_='breadcrumbs-plus')
        if section_line is not None:
            section = section_line.find('a', title=True)
            if section is not None:
                data['sch:articleSection'] = section.text.strip()
            else:
                print("rovat nincs", url)
        else:
            tei_logger.log('WARNING', f'{url}: SECTION TAG NOT FOUND!')
        authors = bs.find('h6', class_='entry-meta')
        if authors is not None:
            authors_string = authors.text.strip()
            if len(authors_string) > 0 and ' és ' not in authors_string:
                data['sch:author'] = [authors_string[authors_string.find(':')+1:]]
        else:
            tei_logger.log('WARNING', f'{url}: AUTHOR TAG NOT FOUND!')
        keywords_root = bs.find('section', class_='tags-section')
        if keywords_root is not None:
            keywords_list = [a.text.strip() for a in keywords_root.find_all('a', rel='tag') if a is not None]
            data['sch:keywords'] = keywords_list
        return data
    else:
        tei_logger.log('WARNING', f'{url}: ARTICLE BODY CONTAINER NOT FOUND!')
        return None


def excluded_tags_spec(tag):
    return tag


BLOCK_RULES_SPEC = {}
BIGRAM_RULES_SPEC = {}
LINKS_SPEC = BASIC_LINK_ATTRS
DECOMP = [(('section',), {'class': 'share-section'}),
          (('section',), {'class': 'tags-section'}),
          (('script',), {})]
MEDIA_LIST = []


def decompose_spec(article_dec):
    decompose_listed_subtrees_and_mark_media_descendants(article_dec, DECOMP, MEDIA_LIST)
    return article_dec
    # "A cikket a Semmelweis Egyetem Kommunikációs és Rendezvényszervezési Igazgatósága tette közzé."


BLACKLIST_SPEC = ['https://semmelweis.hu/klinikaikozpont/gyik-covid-pcr/',
                  'https://semmelweis.hu/hirek/2020/07/31/koronavirus-a-kulfoldrol-hazaterok-koltsegterites-elleneben'
                  '-tesztelhetik-magukat-a-semmelweis-egyetem-laborjaiban/',
                  'https://semmelweis.hu/hirek/2020/08/08/a-semmelweis-polgaroknak-tovabbra-is-ingyenes-a-pcr-szures/']

MULTIPAGE_URL_END = re.compile(r'^\b$')  # Dummy


def next_page_of_article_spec(_):
    return None
