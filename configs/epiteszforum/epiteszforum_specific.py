#!/usr/bin/env python3
# -*- coding: utf-8, vim: expandtab:ts=4 -*

import re

from html2tei import parse_date, BASIC_LINK_ATTRS, decompose_listed_subtrees_and_mark_media_descendants, tei_defaultdict

PORTAL_URL_PREFIX = 'https://epiteszforum.hu'

ARTICLE_ROOT_PARAMS_SPEC = [(('div',), {'class': 'rightGap'}),
                            (('div',), {'class': 'galleryArticle'})]
# gallery: https://epiteszforum.hu/egy-koncepcio-szaztiz-tortenet-kolontar-es-devecser-uj-utcai-tiz-ev-utan


def get_meta_from_articles_spec(tei_logger, url, bs):
    data = tei_defaultdict()
    data['sch:url'] = url
    date_root = bs.find('div', class_='dateAndSocials')
    if date_root:
        pub_date = bs.find('div', class_='date')
        if pub_date:
            parsed_date = parse_date(pub_date.text.strip(), '%Y.%m.%d. %H:%M')
            if parsed_date:
                data['sch:datePublished'] = parsed_date
            else:
                tei_logger.log('WARNING', f'{url}: DATE FORMAT ERROR!')
    else:
        tei_logger.log('WARNING', f'{url}: DATE NOT FOUND IN URL!')
    title = bs.find('h1')
    if title:
        data['sch:name'] = title.text.strip()
    else: tei_logger.log('WARNING', f'{url}: TITLE NOT FOUND IN URL!')
    rest_as_keyword = []
    meta_root = bs.find('div', class_='sidebarInfos')
    if meta_root is None:
        meta_root = bs.find('div', class_='textCols clearfix')  # gallery articles
    if meta_root:
        author_p = [p for p in meta_root.find_all(['p', 'h4']) if len(p.text.strip()) > 0]
        for p in author_p:
            p_text = p.text.strip()
            if p_text.startswith('Szerzők'):
                authors = [a.text.strip().replace('Fotók: ', '') for a in p.find_all('a')]
                data['sch:author'] = authors
            elif p_text.startswith('Földrajzi'):
                places = [a.text.strip() for a in p.find_all('a')]
                data['sch:contentLocation'] = places
            elif p_text.startswith('Építészek'):
                artist = [a.text.strip() for a in p.find_all('a')]
                data['sch:artist'] = artist
            elif p.text.strip().startswith('Vélemények:') or p.text.strip().startswith('További') \
                    or p.text.strip().startswith('Letölthető'):
                break
            else:
                rest_as_keyword.extend([a.text.strip() for a in p.find_all('a') if len(a.text.strip()) > 0])
        # metadata categories can be developed with the followings:
        # Cég, szervezet:
        # https://epiteszforum.hu/irodahazak-ejszakaja-vi-well-iroda   sourceOrganization Termék, technológia:
        # https://epiteszforum.hu/tetoablak-trend-energiamegtakaritas-es-ujrahasznosithatosag Letölthető
        # dokumentumok: https://epiteszforum.hu/belteri-falfelulet-megformalasa-a-nyiregyhazi-foiskola-tanszeki
        # -epulet-beruhazasahoz-kapcsolodva17 Térkép
        # https://epiteszforum.hu/alairtak-a-zeneakademia-epuletenek-rekonstrukciojat-celzo-108-milliard-forintrol
        # -szolo-tamogatasi-szerzodest címkék https://epiteszforum.hu/club-aliga-ahogyan-mar-sosem-fogjuk-latni
        # dosszié, projektinfó/földrajzi hely: https://epiteszforum.hu/elso-napunk-a-velencei-epiteszeti-biennalen
        if len(rest_as_keyword) > 0:
            data['sch:keywords'] = rest_as_keyword
    else:
        tei_logger.log('WARNING', f'{url}: AUTHOR AND KEYWORD TAG ROOT NOT FOUND!')

    section_root = bs.find('div', class_='data clearfix')
    if not section_root:
        section_root = bs.find('div', class_='type')    # gallery articles
    if section_root:
        sections = section_root.text.strip().split('/')
        main_sec = sections[0].strip()
        data['sch:articleSection'] = main_sec
        if len(sections) > 1:
            sub_sec = sections[1].strip()
            data['subsection'] = sub_sec
    else:
        tei_logger.log('WARNING', f'{url}: SECTION TAG NOT FOUND!')
    return data


def excluded_tags_spec(tag):
    return tag


BLOCK_RULES_SPEC = {}
BIGRAM_RULES_SPEC = {}
LINKS_SPEC = BASIC_LINK_ATTRS
DECOMP = [(('div',), {'class': 'data clearfix'}),
          (('div',), {'class': 'dateAndSocials'}),
          (('div',), {'class': 'col title'}),
          (('div',), {'class': 'adBlock'}),
          (('form',), {'class': 'addComment'}),
          # (('table',), {'adBlock': ''}),   decomposed through text_tags-table
          (('div',), {'class': 'adBlock'}),
          (('aside',), {}),
          (('table',), {'imagewithcap': True}),
          (('div',), {'class': 'loginAndReg'}),
          (('div',), {'class': ['sidebarInfos mobile']}),
          (('div',), {'class': 'adBlock'}),
          (('div',), {'class': 'searchWindow'}),
          (('footer',), {}),
          (('script',), {}),
          (('form',), {'class': 'replyBox'}),
          (('div',), {'class': 'cookieLayer'}),
          (('div',), {'class': 'toCenter'}),
          (('div',), {'class': 'col title'}),
          (('div',), {'class': 'col toLeft'}),
          (('div',), {'class': 'steps'})
          ]

MEDIA_LIST = []


def decompose_spec(article_dec):
    article = article_dec.find('div', class_='rightGap')
    if article is not None:
        article.find('h1').decompose()  # the first h1 is the main title
    decompose_listed_subtrees_and_mark_media_descendants(article_dec, DECOMP, MEDIA_LIST)
    return article_dec


BLACKLIST_SPEC = []

LINK_FILTER_SUBSTRINGS_SPEC = re.compile('|'.join(['LINK_FILTER_DUMMY_STRING']))

MULTIPAGE_URL_END = re.compile(r'^\b$')  # Dummy


def next_page_of_article_spec(_):
    return None
