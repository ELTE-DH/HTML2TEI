#!/usr/bin/env python3
# -*- coding: utf-8, vim: expandtab:ts=4 -*

import re

from bs4 import BeautifulSoup

from html2tei import parse_date, BASIC_LINK_ATTRS, decompose_listed_subtrees_and_mark_media_descendants, tei_defaultdict

PORTAL_URL_PREFIX = 'https://telex.hu/rovat/koronavirus'

ARTICLE_ROOT_PARAMS_SPEC = [(('div',), {'class': 'article_container_'})]


def get_meta_from_articles_spec(tei_logger, url, bs):
    data = tei_defaultdict()
    data['sch:url'] = url
    article_root = bs.find('div', id='cikk-content')  # <div id="cikk-content" class="">
    if article_root:
        pub_date = article_root.find('p', id='original_date')
        if pub_date is not None:
            parsed_date = parse_date(pub_date.text.strip(), '%Y. %B %d. – %H:%M')  # 2021. január 31. – 15:13
            if parsed_date is not None:
                data['sch:datePublished'] = parsed_date
            else:
                tei_logger.log('WARNING', f'{url}  MISSING DATE OR UNKNOWN DATE FORMAT')

        title = article_root.find('h1', class_='article-h1')
        if title:
            data['sch:name'] = title.text.strip()
        else:
            tei_logger.log('WARNING', f'{url}: TITLE NOT FOUND IN URL!')
        authors = [author.text.strip() for author in article_root.find_all('div', class_='author')]
        # <div data-v-083a3177="" class="article_author">
        post_authors = [author.em.text.strip() for author in article_root.find_all('div', class_='article_author')]
        if len(post_authors) > 0:
            authors.extend(list(set(post_authors)))
        if len(authors) > 0:
            data['sch:author'] = authors
        elif len(authors) > 1:
            tei_logger.log('WARNING', f'{url}: AUTHOR TAG NOT FOUND!')

        tags = [a.attrs['content'] for a in bs.find_all('meta', {'name': 'article:tag'})]
        section_tags = [section_tag.text.strip() for section_tag in bs.find_all('a', class_='super tag')]
        if len(section_tags) > 0:
            data['sch:articleSection'] = section_tags[0]
        if len(tags) > 1:
            tags.remove(section_tags[0])
            # For articles on coronavirus topics, we use the "koronavirus" keyword as a column.
            data['sch:keywords'] = tags
        else:
            tei_logger.log('WARNING', f'{url}: TAGS NOT FOUND!')
        return data
    tei_logger.log('WARNING', f'{url}: ARTICLE BODY NOT FOUND!')
    return None


def excluded_tags_spec(tag):
    return tag


BLOCK_RULES_SPEC = {}
BIGRAM_RULES_SPEC = {}
LINKS_SPEC = BASIC_LINK_ATTRS
DECOMP = [(('div',), {'class': 'sidebar_container_'}),
          (('div',), {'class': 'top-section'}),
          (('div',), {'class': 'info-spacing-article'}),
          (('div',), {'class': 'article-bottom'}),
          (('div',), {'class': 'recommendation-block'}),
          (('div',), {'class': 'pagination'})]


MEDIA_LIST = []


def decompose_spec(article_dec):
    decompose_listed_subtrees_and_mark_media_descendants(article_dec, DECOMP, MEDIA_LIST)
    return article_dec


BLACKLIST_SPEC = []

MULTIPAGE_URL_END = re.compile(r'.*oldal=.')


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
