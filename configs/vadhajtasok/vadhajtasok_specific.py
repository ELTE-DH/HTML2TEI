#!/usr/bin/env python3
# -*- coding: utf-8, vim: expandtab:ts=4 -*

import re

from os.path import join as os_path_join, dirname as os_path_dirname, abspath as os_path_abspath
from html2tei import parse_date, BASIC_LINK_ATTRS, decompose_listed_subtrees_and_mark_media_descendants, tei_defaultdict

PORTAL_URL_PREFIX = 'https://www.vadhajtasok.hu/'

ARTICLE_ROOT_PARAMS_SPEC = [(('div',), {'class': 'entry-content content-article'})]

HTML_BASICS = {'p', 'h3', 'h2', 'h4', 'h5', 'em', 'i', 'b', 'strong', 'mark', 'u', 'sub', 'sup', 'del', 'strike',
               'ul', 'ol', 'li', 'table', 'tr', 'td', 'th', 'quote', 'figure', 'iframe', 'script', 'noscript'}

SOURCE_1 = ['Forrás:', 'Írta:']
SOURCE_2 = ['Vadhajtasok.hu', 'Pestisracok.hu', '888.hu', 'MTI', 'Magyar Nemzet', 'HVG']
# If we stay at the current solution (see the get_meta_from_articles_spec function) and use
# both SOURCE_1 and SOURCE_2 lists, then we will be able to find the majority of the sources but not all of them.
# Note: the SOURCE_2 list is not complete, can still be improved but with the current routine it is not necessary.


def get_meta_from_articles_spec(tei_logger, url, bs):
    data = tei_defaultdict()
    data['sch:url'] = url
    article_root = bs.find('div', class_='entry-content content-article')
    info_root = bs.find('div', class_='cs-entry__header-info')
    if article_root is not None:
        if info_root is not None:
            section_date_tag = info_root.find('div', class_='cs-entry__post-meta f16 meta-tiny')
            if section_date_tag is not None:
                section_main = section_date_tag.find('a', class_='meta-categories')
                if section_main is not None:
                    data['sch:articleSection'] = section_main.text.strip()
                else:
                    tei_logger.log('WARNING', f'{url}: SECTION TAG NOT FOUND!')
                date_tag = section_date_tag.find('div', class_='cs-meta-date',
                                                 string=re.compile(r'\d{4}\. .*\d{2}:\d{2}'))
                if date_tag is not None:
                    parsed_date = parse_date(date_tag.text.strip(), '%Y. %B %d. - %H:%M')
                    if parsed_date is not None:
                        data['sch:datePublished'] = parsed_date
                    else:
                        tei_logger.log('WARNING', f'{url}: DATE TEXT FORMAT ERROR!')
                else:
                    tei_logger.log('WARNING', f'{url}: DATE TAG NOT FOUND!')
            else:
                tei_logger.log('WARNING', f'{url}: SECTION & DATE TAG NOT FOUND!')
            modified_date_tag = info_root.find('span', class_='pk-badge pk-badge-no-danger',
                                               string=re.compile(r'Frissítve! - \d{4}\. .*\d{2}:\d{2}'))
            if modified_date_tag is not None:
                modified_date_text = modified_date_tag.text.replace('Frissítve! - ', '').strip()
                parsed_modified_date = parse_date(modified_date_text,  '%Y. %B %d. - %H:%M')
                if parsed_modified_date is not None:
                    data['sch:dateModified'] = parsed_modified_date
                else:
                    tei_logger.log('WARNING', f'{url}: MODIFIED DATE TEXT FORMAT ERROR!')
            title = info_root.find('h1', class_='cs-entry__title')
            if title is not None:
                article_title = title.find('span')
                data['sch:name'] = article_title.text.strip()
            else:
                tei_logger.log('WARNING', f'{url}: TITLE NOT FOUND IN URL!')
        keywords_root = bs.find('ul', class_='post-categories')
        if keywords_root is not None:
            keywords_list = [t.text.strip() for t in keywords_root.find_all('a', class_='news-tag')]
            if len(keywords_list) > 0:
                data['sch:keywords'] = keywords_list
        else:
            tei_logger.log('DEBUG', f'{url}: TAGS NOT FOUND!')
        # Problem: the sources of the articles are NOT handled in a standard manner at vadhajtasok.hu
        # This routine tries to reach as many sources as possible in an automated manner but it can be improved.
        source_root = bs.find_all('strong')
        if len(source_root) == 1:
            source_raw = source_root[0].text.strip()
            # If there is only one element in source_root, we use SOURCE_1,
            # because we would like to find only the source-related texts.
            if any(src in source_raw for src in SOURCE_1):
                source = source_raw.replace('Forrás: ', '').replace('Írta: ', '')
                data['sch:source'] = source
        elif len(source_root) > 1:
            # If there are several elements in source_root, we use the latest one of them,
            # because that's where the sources are stored in the majority of the cases.
            source_raw = source_root[-1].text.strip()
            # In this case we use both SOURCE_1 and SOURCE_2.
            if any(src in source_raw for src in (SOURCE_1 + SOURCE_2)):
                source = source_raw.replace('Forrás: ', '').replace('Írta: ', '')
                data['sch:source'] = source
        else:
            tei_logger.log('DEBUG', f'{url}: SOURCE NOT FOUND!')
        return data
    else:
        tei_logger.log('WARNING', f'{url}: ARTICLE BODY NOT FOUND!')
        return None


def excluded_tags_spec(tag):
    if tag.name not in HTML_BASICS:
        tag.name = 'else'
    tag.attrs = {}
    return tag


BLOCK_RULES_SPEC = {}
BIGRAM_RULES_SPEC = {}
LINKS_SPEC = BASIC_LINK_ATTRS
DECOMP = [(('script',), {})]

MEDIA_LIST = [(('table',), {}),
              (('figure',), {}),
              (('img',), {}),
              (('iframe',), {}),
              (('div',), {'class': 'twitter-tweet twitter-tweet-rendered'})]


def decompose_spec(article_dec):
    decompose_listed_subtrees_and_mark_media_descendants(article_dec, DECOMP, MEDIA_LIST)
    return article_dec


BLACKLIST_SPEC = [url.strip() for url in open(
    os_path_join(os_path_dirname(os_path_abspath(__file__)), 'vadhajtasok_BLACKLIST.txt')).readlines()]

LINK_FILTER_SUBSTRINGS_SPEC = re.compile('|'.join(['LINK_FILTER_DUMMY_STRING']))

MULTIPAGE_URL_END = re.compile(r'^\b$')  # Dummy


def next_page_of_article_spec(_):
    return None