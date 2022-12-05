#!/usr/bin/env python3
# -*- coding: utf-8, vim: expandtab:ts=4 -*-

import re
from os.path import join as os_path_join, dirname as os_path_dirname, abspath as os_path_abspath

from src.html2tei import parse_date, decompose_listed_subtrees_and_mark_media_descendants, tei_defaultdict

PORTAL_URL_PREFIX = 'https://magyarnemzet.hu'
ARTICLE_ROOT_PARAMS_SPEC = [(('div',), {'class': 'entry-content'})]


def get_meta_from_articles_spec(tei_logger, url, bs):
    data = tei_defaultdict()
    data['sch:url'] = url
    article_root = bs.find('article')
    if article_root is None:
        return None
    else:
        date_tag = bs.find('span', class_='en-article-dates-main')
        if date_tag is not None:
            parsed_date = parse_date(date_tag.text.strip(), '%Y. %B %d. %A %H:%M')
            if parsed_date is not None:
                data['sch:datePublished'] = parsed_date
            else:
                tei_logger.log('WARNING', f'{url}  UNKONOWN DATE FORMAT')
        else:
            tei_logger.log('WARNING', f'{url}  MISSING DATE')
        modified_date_tag = bs.find('span', class_='en-article-dates-updated')
        if modified_date_tag is not None:
            parsed_modified_date = parse_date(modified_date_tag.text.strip(), '%Y. %m. %d. %H:%M')
            if parsed_modified_date is not None:
                data['sch:dateModified'] = parsed_modified_date
            else:
                tei_logger.log('WARNING', f'{url} UNKONOWN MODIFIED DATE FORMAT')
        else:
            tei_logger.log('DEBUG', f'{url}  MISSING DATE')
        title = article_root.find('div', class_='et_main_title')
        if title is not None:
            data['sch:name'] = title.text.strip()
        else:
            tei_logger.log('WARNING', f'{url}  TITLE TAG NOT FOUND!')
        subtitle = article_root.find('div', class_='en-article-subtitle')
        if subtitle is not None:
            data['sch:alternateName'] = subtitle.text.strip()
        author = article_root.find('div', class_='en-article-author')
        source = article_root.find('div', class_='en-article-source col-sm')
        if author is not None:
            data['sch:author'] = [author.text.strip()]
        elif source is not None:
            data['sch:source'] = source.text.strip()
        else:
            tei_logger.log('DEBUG', f'{url}  AUTHOR AND SOURCE TAG NOT FOUND!')

        section_tag = article_root.find('span', class_='en-article-header-column')
        if section_tag is not None:
            sections = [c.text.strip() for c in section_tag.find_all('a') if c.text.strip() != 'Archívum']
            if len(sections) > 0:
                data['sch:articleSection'] = sections[0]
                if len(sections) > 1:
                    data['subsection'] = sections[1]
        else:
            tei_logger.log('WARNING', f'{url}  SECTION TAG NOT FOUND!')
        keywords_root = article_root.find('div', class_='en-article-tags')
        if keywords_root is not None:
            keywords_list = [a.text.strip() for a in keywords_root.find_all('a')]
            data['sch:keywords'] = keywords_list
        else:
            tei_logger.log('DEBUG', f'{url}  KEYWORDS NOT FOUND!')
        return data


def excluded_tags_spec(tag):
    if 'cikk_kep' in tag.name:
        tag.name = 'cikk_kep'
    return tag


BLOCK_RULES_SPEC = {}
BIGRAM_RULES_SPEC = {'bekezdes': {('media_hivatkozas', 'to_merge'): ('media_tartalom', 'media_hivatkozas')}}

LINKS_SPEC = {'a', '0_MDESC_a', 'img', '0_MDESC_img', 'iframe', '0_MDESC_iframe', 'input', 'object'}

DECOMP = [(('script',), {}),
          (('div',), {'class': 'et_pb_section'}),
          (('footer',), {}),
          (('div',), {'id': 'sidebar'}),
          (('div',), {'id': 'miArchivePopUp-window'}),
          (('div',), {'id': 'et-footer-primary-nav'}),
          (('div',), {'id': 'et-footer-nav'}),
          (('div',), {'class': 'offererContent'}),
          (('div',), {'class': 'et_pb_article_offerer'}),
          (('div',), {'class': 'enews-article-offerer'}),
          (('div',), {'class': 'mcePaste'})]

MEDIA_LIST = [(('div',), {'class': '\"image'})]


def decompose_spec(article_dec):
    decompose_listed_subtrees_and_mark_media_descendants(article_dec, DECOMP, MEDIA_LIST)
    return article_dec


BLACKLIST_SPEC = [url.strip() for url in open(os_path_join(os_path_dirname(os_path_abspath(__file__)),
                                                           'mno_BLACKLIST_bad_encoding.txt')).readlines()] \
                 + ['https://www.magyaridok.hu/belfold/kinek-a-kulturalis-diktaturaja-szakacs-arpad-cikksorozata'
                    '-3287285/',
                     'https://www.magyaridok.hu/kulfold/groteszk-lehallgatasi-botrany-parizsban-2815667/',
                     'https://www.magyaridok.hu/sport/futball-eb/program-junius-10-tol-julius-10-ig-736987/',
                    'https://magyarnemzet.hu/archivum-archivum/2004/02/falinaptar-online-rendeles',
                    'https://magyarnemzet.hu/archivum/archivum-archivum/falinaptar-online-rendeles-5210003/'] + \
                 [url.strip() for url in open(os_path_join(os_path_dirname(os_path_abspath(__file__)),
                                                           'mno_BLACKLIST_empty.txt')).readlines()] + \
                 [url.strip() for url in open(os_path_join(os_path_dirname(os_path_abspath(__file__)),
                                                           'mno_BLACKLIST_empty_plus.txt')).readlines()]


MULTIPAGE_URL_END = re.compile(r'^\b$')  # Dummy
LINK_FILTER_SUBSTRINGS_SPEC = re.compile('|'.join(['LINK_FILTER_DUMMY_STRING']))


def next_page_of_article_spec(_):
    return None
