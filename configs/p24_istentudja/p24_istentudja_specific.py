#!/usr/bin/env python3
# -*- coding: utf-8, vim: expandtab:ts=4 -*

import re

from src.html2tei import parse_date, BASIC_LINK_ATTRS, decompose_listed_subtrees_and_mark_media_descendants, tei_defaultdict

PORTAL_URL_PREFIX = 'https://istentudja.24.hu/'

ARTICLE_ROOT_PARAMS_SPEC = [(('div',), {'class': 'o-post'})]


SOURCE = '24.hu'
SECTION = 'isten tudja'


def get_meta_from_articles_spec(tei_logger, url, bs):
    data = tei_defaultdict()
    data['sch:url'] = url
    article_root = bs.find('div', class_='site-content')
    if article_root is None:
        tei_logger.log('WARNING', f'{url}: ARTICLE ROOT NOT FOUND/UNKNOWN ARTICLE SCHEME!')
        return None
    date_tag = bs.find('div', class_='m-author__wrapCatDateTitulus')
    if date_tag is not None:
        titulus = date_tag.find('span')
        if titulus is not None:
            titulus.decompose()
        parsed_date = parse_date(date_tag.text.strip(), '%Y. %m. %d. %H:%M')
        if parsed_date is not None:
            data['sch:datePublished'] = parsed_date
        else:
            tei_logger.log('WARNING', f'{url}: DATE FORMAT ERROR!')
    else:
        tei_logger.log('WARNING', f'{url}: DATE NOT FOUND IN URL!')
    modified_date_tag = bs.find('meta', property='article:modified_time')
    if modified_date_tag is not None:
        parsed_moddate = parse_date(modified_date_tag.attrs['content'][:19], '%Y-%m-%dT%H:%M:%S')
        if parsed_moddate is not None:
            data['sch:dateModified'] = parsed_moddate
        else:
            tei_logger.log('WARNING', f'{url}: MODIFIED DATE FORMAT ERROR!')
    else:
        tei_logger.log('DEBUG', f'{url}: MODIFIED DATE NOT FOUND IN URL!')
    keywords = bs.find('meta', {'name': 'keywords', 'content': True})
    if keywords is not None:
        keywords_list = keywords['content'].split(',')
        while SECTION in keywords_list:
            keywords_list.remove(SECTION)
        data['sch:keywords'] = keywords_list
    else:
        tei_logger.log('WARNING', f'{url}: KEYWORDS NOT FOUND!')
    title = article_root.find('h1', class_='o-post__title')
    if title is not None:
        data['sch:name'] = title.text.strip()
    else:
        tei_logger.log('WARNING', f'{url}: TITLE TAG NOT FOUND!')
    author = article_root.find_all('a', class_='m-author__imgLink')
    if len(author) > 0:
        authors = []
        for i in author:
            author_tag = i.find('img', {'alt': True})
            if author_tag is not None:
                authors.append(author_tag['alt'])
        if SOURCE in authors:
            data['sch:source'] = [SOURCE]
            authors.remove(SOURCE)
        if len(authors) > 0:
            data['sch:author'] = authors
    else:
        tei_logger.log('WARNING', f'{url}: AUTHOR TAG NOT FOUND!')
    data['sch:articleSection'] = SECTION
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
DECOMP = [(('div',), {'class': 'o-post__author'}),
          (('div',), {'class': 'o-post__summary'}),
          (('h1',), {'class': 'o-post__title'}),
          (('div',), {'class': 'banner-container'}),
          (('div',), {'class': 'shareItemLikeBox'}),
          (('p',), {'class': '_ce_measure_widget'}),
          (('div',), {'id': 'post-tags-section-1'}),
          (('div',), {'id': 'post-tags-section-2'}),
          (('div',), {'class': 'a-hirstartRecommender'}),
          (('div',), {'class': 'm-articRecommend__cntWrap'}),
          (('div',), {'class': 'm-post__wrap'}),
          (('div',), {'data-ce-measure-widget': 'Cikkvégi gombok'}),
          (('script',), {}),
          (('style',), {})]

MEDIA_LIST = []


def decompose_spec(article_dec):
    decompose_listed_subtrees_and_mark_media_descendants(article_dec, DECOMP, MEDIA_LIST)
    return article_dec


BLACKLIST_SPEC = []

LINK_FILTER_SUBSTRINGS_SPEC = re.compile('|'.join(['LINK_FILTER_DUMMY_STRING']))

MULTIPAGE_URL_END = re.compile(r'^\b$')  # Dummy


def next_page_of_article_spec(_):
    return None
