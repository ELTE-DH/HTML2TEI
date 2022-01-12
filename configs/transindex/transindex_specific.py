#!/usr/bin/env python3
# -*- coding: utf-8, vim: expandtab:ts=4 -*

import re

from os.path import join as os_path_join, dirname as os_path_dirname, abspath as os_path_abspath
from html2tei import parse_date, BASIC_LINK_ATTRS, decompose_listed_subtrees_and_mark_media_descendants, tei_defaultdict

PORTAL_URL_PREFIX = 'https://transindex.ro'

ARTICLE_ROOT_PARAMS_SPEC = [(('article',), {'class': 'page-left-side'}),
                            (('td',), {'id': 'ElsoTartalom'})   # tech, sárm
                            # https://eletmod.transindex.ro/?hir=13920
                            # https://multikult.transindex.ro/?cikk=14287
                            # https://vilag.transindex.ro/?hir=19427
                            # https://eletmod.transindex.ro/?hir=13448
                            # https://itthon.transindex.ro/?hir=47909
                            # https://sport.transindex.ro/?cikk=23232
                            # https://welemeny.transindex.ro/?cikk=13959
                            #  https://sarm.transindex.ro/?cikk=5369
                            #  https://tech.transindex.ro/?hir=32
                            ]
SECTION_DICT = {'sarm': 'Sárm',
                'tech': 'Tech',
                'multikult': 'Multikult',
                'sport': 'Sport',
                'eletmod': 'Életmód',
                'itthon': 'Itthon',
                'vilag': 'Világ',
                'welemeny': 'Vélemény',
                'penz': 'Pénz',
                'think': 'Think'}


def get_meta_from_articles_spec(tei_logger, url, bs):
    data = tei_defaultdict()
    data['sch:url'] = url
    section = url[url.find('://') + 3:url.find('.')]
    if section in SECTION_DICT.keys():
        data['sch:articleSection'] = SECTION_DICT[section]
    else:
        tei_logger.log('WARNING', f'{url}: SECTION TAG NOT FOUND!')
    if section not in {'tech', 'sarm', 'penz'}:
        header = bs.find_all('header')
        if len(header) > 1:
            header = header[1]
            date_tag = header.find('span', class_='date')
            if date_tag is not None:    # 2021. május 27. 12:00, utolsó frissítés: 12:02 - a Transindex.ro portálról
                dates = date_tag.text.strip().split(',')
                parsed_date = parse_date(dates[0], '%Y. %B %d. %H:%M')
                if parsed_date is not None:
                    data['sch:datePublished'] = parsed_date
                else:
                    tei_logger.log('WARNING', f'{url}: DATE TEXT FORMAT ERROR!')
                mod_date = dates[1].strip()
                if mod_date.startswith('utolsó') and '201' not in mod_date and '202' not in mod_date \
                        and '200' not in mod_date:
                    mod_date = (dates[0][:(dates[0].find(':')-2)])+(mod_date[mod_date.find(': ')+2:mod_date.find(' -')])
                else:
                    mod_date = mod_date[18:]
                parsed_moddate = parse_date(mod_date, '%Y. %B %d. %H:%M')
                if parsed_moddate is not None:
                    data['sch:dateModified'] = parsed_moddate
                else:
                    tei_logger.log('WARNING', f'{url}, {mod_date}: MODIFIED DATE TEXT FORMAT ERROR!')
            else:
                tei_logger.log('WARNING', f'{url}: DATE TAG NOT FOUND!')

            title = header.find('h1')
            if title is not None:
                title = title.text.strip()
                data['sch:name'] = title
            else:
                title = bs.find('h1')
                if title is not None:
                    title = title.text.strip()
                    data['sch:name'] = title
                else:
                    tei_logger.log('WARNING', f'{url}: TITLE NOT FOUND IN URL!')
            author = header.find('span', class_='writer')
            if author is not None:
                data['sch:keywords'] = [author.text.strip()]
            else:
                tei_logger.log('DEBUG', f'{url}: TAGS NOT FOUND!')

            return data

    elif section in {'tech', 'sarm'}:
        date_tag = bs.find('ul', {'id': 'UtolsoModP1'})
        if date_tag is not None:
            # <li>Utolsó frissítés: 16:54 GMT +2, <b>2007. március 22.</b></li>
            date_day = date_tag.find('b')
            hour_min = date_tag.find('li').text.strip()[18:23]  # Utolsó frissítés: 16:54 GMT +2,
            date = f'{date_day.text.strip()} {hour_min}'
            parsed_date = parse_date(date, '%Y. %B %d. %H:%M')
            if parsed_date is not None:
                data['sch:datePublished'] = parsed_date
            else:
                # <ul id="UtolsoModP1"><li>Utolsó frissítés: 12: 1 GMT +2, <b>2007. 2-.</b></li></ul>
                parsed_date = parse_date(date_day.text.strip()[:4], '%Y')
                if parsed_date is not None:
                    data['sch:datePublished'] = parsed_date
                else:
                    tei_logger.log('WARNING', f'{url}: DATE/YEAR TEXT FORMAT ERROR!')
        else:
            tei_logger.log('WARNING', f'{url}: DATE TAG NOT FOUND!')
        title = bs.find('span', class_='MagazinCim')
        if title is not None:
            title_text = title.text.strip()
            data['sch:name'] = title_text
        else:
            tei_logger.log('WARNING', f'{url}: TITLE NOT FOUND IN URL!')
        subtitle_tag = bs.find('span', class_='MagazinAlcim')
        if subtitle_tag is not None:
            subtitle = subtitle_tag.text.strip()
            data['sch:alternateName'] = subtitle
        else:
            tei_logger.log('DEBUG', f'{url}: TITLE NOT FOUND IN URL!')
        author = bs.find('span', class_='MagazinSzerzo')
        if author is not None:
            data['sch:author'] = [author.text.strip()]
        else:
            tei_logger.log('DEBUG', f'{url}: AUTHOR TAG NOT FOUND!')
        return data
    elif section not in {'penz', 'sport'}:
        # The articles of 'penz' and 'sport' column cannot be processed, because these links redirect to th main page.
        # (Archiving these columns is under construction.)
        tei_logger.log('WARNING', f'{url}: UNKNOW ARTICLE SCHEMA!')
        return None


def excluded_tags_spec(tag):
    return tag


BLOCK_RULES_SPEC = {}
BIGRAM_RULES_SPEC = {'kviz': {('kiemelt', 'det_by_any_desc'): ('kviz', 'kerdes')}}
LINKS_SPEC = BASIC_LINK_ATTRS
DECOMP = [  # (('header',), {}),
    (('div',), {'class': 'like-box'}),
    (('div',), {'class': 'only-smartphone'}),
    (('div',), {'class': 'no-smartphone'}),
    (('div',), {'class': 'fb-like'}),
    (('div',), {'id': 'lajkolj'}),
    (('section',), {'class': 'page-left-side rovat'}),
    (('iframe',), {'title': True}),
    (('p',), {'class': 'MagazinCikk'}),
    (('ul',), {'class': 'HirReklam'}),
    (('p',), {'class': 'HirReklamP'}),
    (('div',), {'id': "Kapcsolodok"}),
    (('div',), {'class': "kommentBigDiv"}),
    (('div',), {'class': 'like'}),
    (('div',), {'id': 'MagazinReklam'}),
    (('ul',), {'id': 'UtolsoModP1'}),
    (('script',), {}),
    (('STYLE',), {}),
    (('style',), {}),
    (('section',), {'class': 'related'}),
    (('div',), {'id': 'CikkHozzaszolas'}),
    (('aside',), {'id': 'popup'}),
    (('span',), {'class': 'elval'})
]


MEDIA_LIST = []


def decompose_spec(article_dec):
    header = article_dec.find('header')
    if header is not None:
        if 'tv.transindex.ro' not in header.text:
            header.decompose()
        else:
            print(header.find('h1').text)
    decompose_listed_subtrees_and_mark_media_descendants(article_dec, DECOMP, MEDIA_LIST)
    return article_dec


BLACKLIST_SPEC = [url.strip() for url in
                  open(os_path_join(os_path_dirname(os_path_abspath(__file__)), 'transindex_BLACKLIST.txt')).readlines()]

MULTIPAGE_URL_END = re.compile(r'^\b$')  # Dummy

LINK_FILTER_SUBSTRINGS_SPEC = re.compile('|'.join(['LINK_FILTER_DUMMY_STRING']))


def next_page_of_article_spec(_):
    return None
