#!/usr/bin/env python3
# -*- coding: utf-8, vim: expandtab:ts=4 -*

import re
from langdetect import detect

from os.path import join as os_path_join, dirname as os_path_dirname, abspath as os_path_abspath
from src.html2tei import parse_date, BASIC_LINK_ATTRS, decompose_listed_subtrees_and_mark_media_descendants,\
    tei_defaultdict

PORTAL_URL_PREFIX = 'https://www.vadhajtasok.hu/'

ARTICLE_ROOT_PARAMS_SPEC = [(('div',), {'class': 'entry-content content-article'})]


# https://www.vadhajtasok.hu/2019/01/05/nagy-szrban-a-9-11-legendaja-hackerek-megszereztek-a-titkos-aktait
SOURCE_2 = ['Vadhajtasok.hu', 'Pestisracok.hu', '888.hu', 'MTI', 'Magyar Nemzet', 'HVG', 'Demokrata', 'Index',
            'Mandiner', 'Origo', 'Vadhajtások', 'Magyar Hírlap', 'hirado.hu', 'Magyar Hírlap', 'V4NA']


def get_meta_from_articles_spec(tei_logger, url, bs):
    data = tei_defaultdict()
    data['sch:url'] = url
    article_root = bs.find('div', class_='entry-content content-article')
    lang = detect(article_root.text)
    if lang == 'en':
        data['sch:availableLanguage'] = 'en'
    info_root = bs.find('div', class_='cs-entry__header-info')
    if article_root is not None:
        if info_root is None:
            tei_logger.log('WARNING', f'{url}: META ROOT NOT FOUND!')
        else:
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
                if article_title is not None:
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
        # CHECK: The source extracting method had been simplified,
        # because the previous solution gave us too many false authors.
        source_root = article_root.find_all(recursive=False)

        if len(source_root) > 0:
            source_raw = source_root[-1].text.strip()
            if len(source_raw) > 0 and len(source_raw.split()) < 6 and \
                    (source_raw.startswith('Forrás:') or source_raw.startswith('Írta:') or
                     source_raw in SOURCE_2):
                data['originalAuthorString'] = [source_raw]
        else:
            tei_logger.log('DEBUG', f'{url}: SOURCE NOT FOUND!')
        return data
    else:
        tei_logger.log('WARNING', f'{url}: ARTICLE BODY NOT FOUND!')
        return None


def excluded_tags_spec(tag):
    return tag


BLOCK_RULES_SPEC = {}
BIGRAM_RULES_SPEC = {}
LINKS_SPEC = BASIC_LINK_ATTRS
DECOMP = [(('script',), {})]

MEDIA_LIST = []


def decompose_spec(article_dec):
    decompose_listed_subtrees_and_mark_media_descendants(article_dec, DECOMP, MEDIA_LIST)
    return article_dec


BLACKLIST_SPEC = [url.strip() for url in open(
    os_path_join(os_path_dirname(os_path_abspath(__file__)), 'vadhajtasok_BLACKLIST.txt')).readlines()]

LINK_FILTER_SUBSTRINGS_SPEC = re.compile('|'.join(['http://%20Kov%C3%A1cs,%20Andr%C3%A1s%20%3Ckovacs.andras3@origo.']))

MULTIPAGE_URL_END = re.compile(r'^\b$')  # Dummy


def next_page_of_article_spec(_):
    return None
