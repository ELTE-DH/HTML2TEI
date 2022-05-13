#!/usr/bin/env python3
# -*- coding: utf-8, vim: expandtab:ts=4 -*

import re

from bs4 import BeautifulSoup
from src.html2tei import parse_date, BASIC_LINK_ATTRS, decompose_listed_subtrees_and_mark_media_descendants, tei_defaultdict

PORTAL_URL_PREFIX = 'https://rangado.24.hu/'

ARTICLE_ROOT_PARAMS_SPEC = [(('div',), {'class': 'o-post'})]

# TODO
#SOURCE = ['Sokszínű Vidék', 'Szponzorált tartalom']


def get_meta_from_articles_spec(tei_logger, url, bs):
    data = tei_defaultdict()
    data['sch:url'] = url
    article_root = bs.find('div', class_='site-content')
    if article_root is None:
        tei_logger.log('WARNING', f'{url}: ARTICLE ROOT NOT FOUND/UNKNOWN ARTICLE SCHEME!')
        return None
    # m-author__catDateTitulusCreateDate
    date_tag = bs.find('span', class_='m-author__catDateTitulusCreateDate')
    if date_tag is None:
        date_tag = bs.find('span', class_='o-post__date')
    if date_tag is not None:
        parsed_date = parse_date(date_tag.text.strip(), '%Y. %m. %d. %H:%M')  # 2021. 04. 06. 20:39
        if parsed_date is not None:
            data['sch:datePublished'] = parsed_date
        else:
            tei_logger.log('WARNING', f'{url}: {date_tag.text.strip()} DATE FORMAT ERROR!')
    else:
        tei_logger.log('WARNING', f'{url}: DATE NOT FOUND IN URL!')
    """    modified_date_tag = bs.find('meta', property='article:modified_time')
    if modified_date_tag is not None:
        parsed_moddate = parse_date(modified_date_tag.attrs['content'][:19], '%Y-%m-%dT%H:%M:%S')"""
    modified_date_tag = bs.find('span', class_='m-author__catDateTitulusUpdateDate')
    if modified_date_tag is not None:
        parsed_moddate = parse_date(modified_date_tag.text.strip().replace('FRISSÍTVE: ', ''), '%Y. %m. %d. %H:%M')
        # <span class="m-author__catDateTitulusUpdateDate">FRISSÍTVE: 2021. 05. 27. 00:30</span>
        if parsed_moddate is not None:
            data['sch:dateModified'] = parsed_moddate
        else:
            tei_logger.log('WARNING', f'{url}: MODIFIED DATE FORMAT ERROR!')
    else:
        mod = bs.find('meta', property='article:modified_time')
        if mod is not None and len(mod.text.strip()) > 0:
            tei_logger.log('WARNING', f'{url}: {mod} MODIFIED DATE EXISTS!')
    keywords = bs.find('meta', {'name': 'keywords', 'content': True})
    if keywords is not None:
        keywords_list = keywords['content'].split(',')
        data['sch:keywords'] = keywords_list
    else:
        tei_logger.log('DEBUG', f'{url}: KEYWORDS NOT FOUND!')
    title = article_root.find('h1', class_='o-post__title')
    if title is not None:
        data['sch:name'] = title.text.strip()
    else:
        tei_logger.log('WARNING', f'{url}: TITLE TAG NOT FOUND!')
    author = article_root.find_all('a', class_='m-author__name')
    if len(author) > 0:
        source_list = []
        authors = []
        author = [i.text.strip() for i in author]
        """[authors.append(i) if i not in SOURCE else source_list.append(i) for i in author]
        if len(source_list) > 0:
            data['sch:source'] = source_list
        if len(authors) > 0:
            data['sch:author'] = authors"""
        data['sch:author'] = author
    else:
        tei_logger.log('WARNING', f'{url}: AUTHOR TAG NOT FOUND!')
    section = article_root.find('a', id='post-cat-title')
    if section is not None:
        data['sch:articleSection'] = section.text.strip()
    else:
        tei_logger.log('DEBUG', f'{url}: SECTION TAG NOT FOUND!')
    return data


def excluded_tags_spec(tag):
    tag_attrs = tag.attrs
    if 'data-hash' in tag_attrs.keys():
        tag_attrs['data-hash'] = '@data-hash'
    if 'data-desc' in tag_attrs.keys():
        tag_attrs['data-desc'] = '@data-desc'
    if 'data-title' in tag_attrs.keys():
        tag_attrs['data-title'] = '@data-title'
    elif tag.name == 'a' and 'id' in tag_attrs.keys():
        tag_attrs['id'] = '@id'
    elif tag.name == 'meta' and 'content' in tag_attrs.keys():
        tag_attrs['content'] = '@content'
    elif tag.name == 'iframe' and 'title' in tag_attrs.keys():
        tag_attrs['title'] = '@title'
    return tag


BLOCK_RULES_SPEC = {}
BIGRAM_RULES_SPEC = {}
LINKS_SPEC = BASIC_LINK_ATTRS

DECOMP = [(('div',), {'class': 'm-articRecommend'}),
          (('div',), {'class': 'o-articleHead'}),
          (('a',), {'class': '-articleHead'}),
          (('div',), {'class': 'o-post__head'}),
          (('div',), {'id': 'content-toggle-placeholder'}),
          (('div',), {'class': 'm-fbComment__txtAndIframeWrap'}),
          (('div',), {'class': 'a-hirstartRecommender'}),
          (('div',), {'class': 'banner_container'}),
          (('div',), {'class': 'm-articleListWidget'}),
          (('div',), {'id': 'post-tags-section'}),
          (('script',), {})]

MEDIA_LIST = [(('iframe',), {'class': 'tableauViz'})]


def decompose_spec(article_dec):
    decompose_listed_subtrees_and_mark_media_descendants(article_dec, DECOMP, MEDIA_LIST)
    return article_dec


BLACKLIST_SPEC = []
LINK_FILTER_SUBSTRINGS_SPEC = re.compile('|'.join(['LINK_FILTER_DUMMY_STRING']))

MULTIPAGE_URL_END = re.compile(r'.*/[1-9]/')
# https://rangado.24.hu/nemzetkozi_foci/2021/05/26/europa-liga-donto-villarreal-manchester-united/2/


def next_page_of_article_spec(curr_html):
    # Rangado 24.hu operates with a reverse multipage logic: the start page is the newest page of the article
    bs = BeautifulSoup(curr_html, 'lxml')
    current_page = bs.find('span', class_='page-numbers current')
    if current_page is not None and current_page.get_text().isdecimal():
        current_page_num = int(current_page.get_text())
        other_pages = bs.find_all('a', class_='page-numbers')
        for i in other_pages:
            # Filter span to avoid other tags with class page-numbers (next page button is unreliable!)
            if i.find('span') is None and int(i.get_text()) + 1 == current_page_num and 'href' in i.attrs.keys():
                next_link = i.attrs['href']
                return next_link
    return None
