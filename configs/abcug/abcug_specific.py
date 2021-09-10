#!/usr/bin/env python3
# -*- coding: utf-8, vim: expandtab:ts=4 -*-

import re

from html2tei import parse_date, BASIC_LINK_ATTRS, decompose_listed_subtrees_and_mark_media_descendants, tei_defaultdict

PORTAL_URL_PREFIX = 'https://abcug.hu'

ARTICLE_ROOT_PARAMS_SPEC = [(('div',), {'class': 'entry-content'}), (('body',), {})]


def get_meta_from_articles_spec(tei_logger, url, bs):
    data = tei_defaultdict()
    data['sch:url'] = url
    article_root = bs.find('header', class_='post-header')
    if article_root is not None:
        date_tag = article_root.find('time')  # <time class="updated" datetime="2019-12-27T13:31:40+01:00">
        if date_tag is not None and 'datetime' in date_tag.attrs.keys():
            parsed_date = parse_date(date_tag.attrs['datetime'][:19], '%Y-%m-%dT%H:%M:%S')
            data['sch:datePublished'] = parsed_date
        else:
            tei_logger.log('WARNING', f'{url}: DATE FORMAT ERROR!')
        title = article_root.find('h1', class_='entry-title')
        if title is not None:
            data['sch:name'] = title.text.strip()
        else:
            title = bs.find('p', class_='matrix-item-title')
            if title is not None:
                data['sch:name'] = title.text.strip()
            else:
                tei_logger.log('WARNING', f'{url}: TITLE NOT FOUND IN URL!')
        authors = article_root.find(class_='byline author')
        if authors is not None:
            authors_list = []
            for a in authors.find_all('a'):
                if ' és ' not in a.text:
                    authors_list.append(a.text.strip())
                else:
                    authors_list.extend(a.text.strip().split(' és '))
            data['sch:author'] = authors_list
        else:
            tei_logger.log('WARNING', f'{url}: AUTHOR TAG NOT FOUND!')
        keywords_root = article_root.find('div', class_='post-information')
        if keywords_root is not None:
            keywords_list = [a.text.strip() for a in keywords_root.find_all('a', rel='tag') if a is not None]
            data['sch:keywords'] = keywords_list
        return data
    else:
        # Single occurrence: https://abcug.hu/kozeposztaly/
        title = bs.find('p', class_='matrix-item-title')
        if title is not None:
            data['sch:name'] = title.text.strip().encode('raw_unicode_escape').decode('UTF-8')
        return data


def excluded_tags_spec(tag):
    tag_attrs = tag.attrs
    if tag.name == 'span' and 'data-scayt_word' in tag_attrs.keys():
        tag_attrs['data-scayt_word'] = '@data-scayt_word'
    return tag


BLOCK_RULES_SPEC = {'idezet': {'rename': {'cimsor': 'felkover'}}, 'lista': {'invalid_inner_blocks': ['cimsor']}}
BIGRAM_RULES_SPEC = {'bekezdes': {('media_hivatkozas', 'det_by_child'): ('media_tartalom', 'media_hivatkozas')}}

LINKS_SPEC = BASIC_LINK_ATTRS
DECOMP = [(('div',), {'class': 'postend-widget'}),
          (('div',), {'class': 'post-information'}),
          (('script',), {})]

MEDIA_LIST = [(('section',), {'class': 'soundcloud-container'}),
              (('figcaption',), {'class': 'soundcloud-container'}),
              (('figure',), {}),
              (('blockquote',), {'class': 'twitter-tweet'}),
              (('blockquote',), {'class': 'twitter-video'}),
              (('div',), {'class': 'fb-post'})]


def decompose_spec(article_dec):
    decompose_listed_subtrees_and_mark_media_descendants(article_dec, DECOMP, MEDIA_LIST)
    return article_dec


BLACKLIST_SPEC = []
LINK_FILTER_SUBSTRINGS_SPEC = re.compile('|'.join(['LINK_FILTER_DUMMY_STRING']))

MULTIPAGE_URL_END = re.compile(r'^\b$')  # Dummy


def next_page_of_article_spec(_):
    return None
