#!/usr/bin/env python3
# -*- coding: utf-8, vim: expandtab:ts=4 -*

import re

from html2tei import parse_date, BASIC_LINK_ATTRS, decompose_listed_subtrees_and_mark_media_descendants, tei_defaultdict

PORTAL_URL_PREFIX = 'https://dummy.hu'

ARTICLE_ROOT_PARAMS_SPEC = [(('div',), {'class': 'post_in'})]


def get_meta_from_articles_spec(tei_logger, url, bs):
    data = tei_defaultdict()
    data['sch:url'] = url
    article_root = bs.find('div', class_='post_in')
    if article_root:
        title = article_root.find('h2')
        if title:
            data['sch:name'] = title.text.strip()
        else:
            tei_logger.log('WARNING', f'{url}: TITLE NOT FOUND IN URL!')
        date_tag = article_root.find('h3', class_='date')
        if date_tag is not None:    # 2012. július 20. 02:07
            parsed_date = parse_date(date_tag.find(text=True).strip(), '%Y. %B %d. %H:%M')
            if parsed_date:
                data['sch:datePublished'] = parsed_date
            else:
                tei_logger.log('WARNING', f'{url}: DATE FORMAT ERROR!')
        else:
            tei_logger.log('WARNING', f'{url}: DATE TAG NOT FOUND!')
        return data
    else:
        tei_logger.log('WARNING', f'{url}: ARTICLE BODY NOT FOUND OR UNKNOWBN ARTICLE SCHEME!')
        return None


def excluded_tags_spec(tag):
    return tag


BLOCK_RULES_SPEC = {}
BIGRAM_RULES_SPEC = {}
LINKS_SPEC = BASIC_LINK_ATTRS
DECOMP = [(('div',), {'id': 'easy-infos'}),
          (('a',), {'class': 'post_anchor'}),
          (('h3',), {'class': 'date'}),  # date
          (('h2',), {}),  # main title
          (('div',), {'class': 'comm'}),
          (('div',), {'class': 'more'}),
          (('div',), {'style': True}),
          (('div',), {'class': 'csatlakozz'}),
          (('div',), {'class': 'post_lablec'}),
          (('div',), {'class': 'linkwithin_div'}),
          (('div',), {'class': 'related'}),
          (('div',), {'class': 'blh-billboard-ad'}),
          (('div',), {'id': 'comment-form'}),
          (('script',), {}),
          (('noscript',), {}),
          (('h3',), {'class': 'comment comment-tracback-url'}),
          (('div',), {'id': 'linkback_container'}),
          (('h3',), {'class': 'comment'}),
          (('p',), {'class': 'comment-disclaimer'}),
          (('div',), {'class': 'linkbacksBg'}),
          (('div',), {'class': 'commentFooter'})    # válasz nyitása a kommentre
          ]

MEDIA_LIST = []


def decompose_spec(article_dec):
    decompose_listed_subtrees_and_mark_media_descendants(article_dec, DECOMP, MEDIA_LIST)
    for a in article_dec.find_all('a', {'name': True}):
        if a.attrs['name'] in {'trackbacks', 'feedbacks', 'pingbacks', 'comments'}:
            a.decompose()
    for p in article_dec.find_all('p'):
        if p.text.strip() == 'Kövesd a Határátkelőt az Instagrammon is!':
            p.decompose()
    return article_dec


BLACKLIST_SPEC = []

LINK_FILTER_SUBSTRINGS_SPEC = re.compile('|'.join(['http://www.exteriores.gob.es/%20Consulados/CARACAS/es/',
                                                   '.*es/%20index.htm$']))
MULTIPAGE_URL_END = re.compile(r'^\b$')  # Dummy


def next_page_of_article_spec(_):
    return None

# to be developed: get unique URL for comments through this (href value): <a class=commentTime href=@LINK title=@title>
# e.g. https://hataratkelo.blog.hu/2012/11/16/europa_utolso_titka
# TESZT:
# https://hataratkelo.blog.hu/2020/07/05/tulelo_uzemmodban_avagy_szep_uj_vilag
