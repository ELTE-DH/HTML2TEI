#!/usr/bin/env python3
# -*- coding: utf-8, vim: expandtab:ts=4 -*

import re

from bs4 import BeautifulSoup

from html2tei import parse_date, BASIC_LINK_ATTRS, decompose_listed_subtrees_and_mark_media_descendants, tei_defaultdict

PORTAL_URL_PREFIX = 'https://forum.kremmania.hu'

ARTICLE_ROOT_PARAMS_SPEC = [(('div',), {'id': 'main-outlet'})]


def get_meta_from_articles_spec(tei_logger, url, bs):
    data = tei_defaultdict()
    data['sch:url'] = url
    article_root = bs.find('div',), {'id': 'main-outlet'}
    if article_root:
        date_tags = bs.find_all('time', {'class': 'post-time', 'datetime': True})
        if len(date_tags) > 0:
            parsed_date = parse_date(date_tags[0].attrs['datetime'][:19], '%Y-%m-%dT%H:%M:%S')
            data['sch:datePublished'] = parsed_date
            parsed_mod_date = parse_date(date_tags[-1].attrs['datetime'][:19], '%Y-%m-%dT%H:%M:%S')
            data['sch:dateModified'] = parsed_mod_date
        else:
            tei_logger.log('WARNING', f'{url}: DATE FORMAT ERROR!')
        title_tag = bs.find('meta', {'property': 'og:title'})
        if title_tag:
            data['sch:name'] = title_tag.attrs['content']
        else:
            tei_logger.log('WARNING', f'{url}: TITLE NOT FOUND IN URL!')
        return data
    else:
        tei_logger.log('WARNING', f'{url}: ARTICLE BODY NOT FOUND!')
        return None


def excluded_tags_spec(tag):
    if 'data-base62-sha1' in tag.attrs.keys():
        tag.attrs['data-base62-sha1'] = '@SIMPLIFIED'
    if 'data-youtube-id' in tag.attrs.keys():
        tag.attrs['data-youtube-id'] = '@ID'
    return tag


BLOCK_RULES_SPEC = {}
BIGRAM_RULES_SPEC = {}
LINKS_SPEC = BASIC_LINK_ATTRS
DECOMP = [(('footer',), {}),
          (('meta',), {}),
          # (('aside',), {}),
          (('div',), {'id': 'topic-title'}),
          (('div',), {'itemprop': 'publisher'}),
          (('span',), {'itemprop': 'position'}),
          (('div',), {'itemprop': 'interactionStatistic'}),
          (('div',), {'role': 'navigation'}),
          (('img',), {'class': 'emoji'}),
          (('link',), {'itemprop': 'mainEntityOfPage'})]


MEDIA_LIST = []


def decompose_spec(article_dec):
    decompose_listed_subtrees_and_mark_media_descendants(article_dec, DECOMP, MEDIA_LIST)
    return article_dec


BLACKLIST_SPEC = []

LINK_FILTER_SUBSTRINGS_SPEC = re.compile('|'.join(['LINK_FILTER_DUMMY_STRING']))

MULTIPAGE_URL_END = re.compile(r'.*\?page=.*')


def next_page_of_article_spec(archive_page_raw_html):
    """extracts and returns next page URL from an HTML code if there is one...
        Specific for https://forum.kremmania.hu (next page of forum topics)
        :returns string of url if there is one, None otherwise"""
    ret = None
    soup = BeautifulSoup(archive_page_raw_html, 'lxml')
    next_page = soup.find('link', rel='next')
    if next_page is not None and next_page.has_attr('href'):
        url_end = next_page.attrs['href']
        ret = f'https://forum.kremmania.hu{url_end}'
    return ret
