#!/usr/bin/env python3
# -*- coding: utf-8, vim: expandtab:ts=4 -*

import re

from bs4 import BeautifulSoup

from html2tei import parse_date, BASIC_LINK_ATTRS, decompose_listed_subtrees_and_mark_media_descendants, tei_defaultdict

PORTAL_URL_PREFIX = 'https://telex.hu/'

ARTICLE_ROOT_PARAMS_SPEC = [(('div',), {'class': 'article_container_'})]


def get_meta_from_articles_spec(tei_logger, url, bs):
    data = tei_defaultdict()
    data['sch:url'] = url
    article_root = bs.find('div', id='cikk-content')  # <div id="cikk-content" class="">
    if article_root:
        date_tag = bs.find('meta', {'name': 'article:published_time'})
        if date_tag is not None and 'content' in date_tag.attrs.keys():
            parsed_date = parse_date(date_tag.attrs['content'][:19], '%Y-%m-%dT%H:%M:%S')
            data['sch:datePublished'] = parsed_date
        else:
            tei_logger.log('WARNING', f'{url}: DATE TAG NOT FOUND!')
        date_mod_tag = bs.find('meta', {'name': 'article:modified_time'})
        if date_mod_tag is not None and 'content' in date_tag.attrs.keys():
            parsed_mod_date = parse_date(date_mod_tag.attrs['content'][:19], '%Y-%m-%dT%H:%M:%S')
            data['sch:dateModified'] = parsed_mod_date
        title = article_root.find('h1')
        if title:
            data['sch:name'] = title.text.strip()
        else:
            tei_logger.log('WARNING', f'{url}: TITLE NOT FOUND IN URL!')
        subtitle = article_root.find('h2')
        if subtitle is not None:
            subtitle_text = subtitle.text.strip()
            if len(subtitle_text) > 0:
                data['sch:alternateName'] = subtitle_text
        authors = [author.text.strip() for author in article_root.find_all('a', class_='author__name')]
        post_authors = []  # authors of news feed
        for p_auth_tag in article_root.find_all('div', class_='article_author'):
            p_auth = p_auth_tag.find('em')
            if p_auth is not None:
                post_authors.append(p_auth.text.strip())
        if len(post_authors) > 0:
            authors.extend(list(set(post_authors)))
        if len(authors) > 0:
            data['sch:author'] = authors
        elif len(authors) > 1:
            tei_logger.log('WARNING', f'{url}: AUTHOR TAG NOT FOUND!')
        tags = [a.attrs['content'] for a in bs.find_all('meta', {'name': 'article:tag'})]
        if len(tags) > 0:
            data['sch:articleSection'] = tags[0]
        if len(tags) > 1:
            tags.remove(tags[0])
            data['sch:keywords'] = tags
        else:
            tei_logger.log('DEBUG', f'{url}: TAGS NOT FOUND!')
        return data
    tei_logger.log('WARNING', f'{url}: ARTICLE BODY NOT FOUND!')
    return None


def excluded_tags_spec(tag):
    return tag


BLOCK_RULES_SPEC = {}
BIGRAM_RULES_SPEC = {'kozvetites_content': {('cimsor', 'det_by_any_desc'): ('to_unwrap', 'cimsor')}}
LINKS_SPEC = BASIC_LINK_ATTRS
DECOMP = [(('div',), {'class': 'sidebar_container_'}),
          (('div',), {'class': 'top-section'}),
          (('div',), {'class': 'info-spacing-article'}),
          (('div',), {'class': 'article-bottom'}),
          (('div',), {'class': 'recommendation-block'}),
          (('div',), {'class': 'pagination'}),
          (('div',), {'class': 'recommendation'}),
          (('p',), {'class': 'adfree'})
          ]


MEDIA_LIST = []


def decompose_spec(article_dec):
    news_offerer = article_dec.find('a', text='A Telex legfrissebb híreit itt olvashatja')
    if news_offerer is not None:
        news_offerer.decompose()
    decompose_listed_subtrees_and_mark_media_descendants(article_dec, DECOMP, MEDIA_LIST)
    return article_dec


BLACKLIST_SPEC = []

MULTIPAGE_URL_END = re.compile(r'.*oldal=.')
LINK_FILTER_SUBSTRINGS_SPEC = re.compile('|'.join(['LINK_FILTER_DUMMY_STRING']))


def next_page_of_article_spec(curr_html):  # https://telex.hu/koronavirus/2020/11/12/koronavirus-pp-2020-11-12/elo
    bs = BeautifulSoup(curr_html, 'lxml')
    if bs.find('div', class_='pagination') is not None:
        current_pagenum = int(bs.find('a', class_='current-page').attrs['href'][-1])
        for pagelink in bs.find_all('a', class_='page'):
            if pagelink.attrs['class'] != ['page', 'current-page']:
                href = pagelink.attrs['href']
                if href[-1].isdigit() and int(href[-1]) == current_pagenum + 1:
                    next_page = f'https://telex.hu{href}'
                    return next_page
    return None
