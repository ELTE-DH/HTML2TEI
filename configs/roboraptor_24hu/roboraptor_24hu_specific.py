#!/usr/bin/env python3
# -*- coding: utf-8, vim: expandtab:ts=4 -*

import re

from html2tei import parse_date, BASIC_LINK_ATTRS, decompose_listed_subtrees_and_mark_media_descendants, tei_defaultdict

PORTAL_URL_PREFIX = 'https://roboraptor.24.hu/'

ARTICLE_ROOT_PARAMS_SPEC = [(('div',), {'class': 'wpb_wrapper'})]

HTML_BASICS = {'p', 'h3', 'h2', 'h4', 'h5', 'em', 'i', 'b', 'strong', 'mark', 'u', 'sub', 'sup', 'del', 'strike',
               'ul', 'ol', 'li', 'table', 'tr', 'td', 'th', 'quote', 'figure', 'iframe', 'script', 'noscript'}

SECTION = 'roboraptor'


def get_meta_from_articles_spec(tei_logger, url, bs):
    data = tei_defaultdict()
    data['sch:url'] = url

    meta_root = bs.find('head')
    if meta_root is not None:
        date_tag = meta_root.find('meta', property='article:published_time')
        if date_tag is None:
            date_tag = meta_root.find('meta', itemprop='datePublished')  # for 'activity' type articles
        if date_tag is not None:
            parsed_date = parse_date(date_tag.attrs['content'][:19], '%Y-%m-%dT%H:%M:%S')
            if parsed_date is not None:
                data['sch:datePublished'] = parsed_date
            else:
                tei_logger.log('WARNING', f'{url}: DATE FORMAT ERROR!')
        else:
            tei_logger.log('WARNING', f'{url}: DATE NOT FOUND IN URL!')

        modified_date_tag = meta_root.find('meta', property='article:modified_time')
        if modified_date_tag is not None:
            parsed_moddate = parse_date(modified_date_tag.attrs['content'][:19], '%Y-%m-%dT%H:%M:%S')
            if parsed_moddate is not None:
                data['sch:dateModified'] = parsed_moddate
            else:
                tei_logger.log('WARNING', f'{url}: MODIFIED DATE FORMAT ERROR!')
        else:
            tei_logger.log('DEBUG', f'{url}: MODIFIED DATE NOT FOUND IN URL!')

        keywords = meta_root.find('meta', {'name': 'keywords', 'content': True})
        if keywords is not None:
            keywords_list = keywords['content'].split(',')
            data['sch:keywords'] = keywords_list
        else:
            tei_logger.log('WARNING', f'{url}: KEYWORDS NOT FOUND!')
    else:
        tei_logger.log('WARNING', f'{url}: META ROOT NOT FOUND!')

    article_root = bs.find('div', class_='site-content')
    if article_root is not None:
        title = article_root.find('h1', class_='o-post__title')
        if title is not None:
            data['sch:name'] = title.text.strip()
        else:
            tei_logger.log('WARNING', f'{url}: TITLE TAG NOT FOUND!')

        author = article_root.find_all('a', class_='m-author__imgLink')
        if len(author) > 0:
            authors = [i.find('img', {'alt': True})['alt'] for i in author]
            if SECTION in authors:
                data['sch:source'] = [SECTION]
                authors.remove(SECTION)
                if len(authors) > 0:
                    data['sch:author'] = authors
            else:
                data['sch:author'] = authors
        else:
            tei_logger.log('WARNING', f'{url}: AUTHOR TAG NOT FOUND!')

        section = article_root.find('a', id='post-cat-title')
        if section is not None:
            data['sch:articleSection'] = section.text.strip()
        else:
            tei_logger.log('DEBUG', f'{url}: SECTION TAG NOT FOUND!')
    else:
        tei_logger.log('WARNING', f'{url}: ARTICLE ROOT NOT FOUND!')

    return data


def excluded_tags_spec(tag):
    if tag.name not in HTML_BASICS:
        tag.name = 'else'
    tag.attrs = {}
    return tag


BLOCK_RULES_SPEC = {}
BIGRAM_RULES_SPEC = {}
LINKS_SPEC = BASIC_LINK_ATTRS
DECOMP = [(('div',), {'class': 'o-post__author'}),
          (('div',), {'class': 'o-post__summary'}),
          (('div',), {'class': 'm-btnsRow'}),
          (('h1',), {'class': 'o-post__title'}),
          (('div',), {'class': 'shareItemLikeBox'}),
          (('div',), {'class': 'banner-container'}),
          (('div',), {'class': 'm-tag__wrap'}),
          (('div',), {'class': 'widget'}),
          (('p',), {'class': '_ce_measure_widget'}),
          (('div',), {'class': 'a-hirstartRecommender'}),
          (('script',), {}),
          (('style',), {})]

MEDIA_LIST = [(('figure',), {}),
              (('iframe',), {}),
              (('video',), {}),
              (('div',), {'class': 'm-videoArtic__wrap'}),
              (('blockquote',), {'class': 'twitter-tweet'}),
              (('div',), {'class': 'fb-video'}),
              (('div',), {'class': 'fb-post-embed'})
              ]


def decompose_spec(article_dec):
    decompose_listed_subtrees_and_mark_media_descendants(article_dec, DECOMP, MEDIA_LIST)
    return article_dec


BLACKLIST_SPEC = ['https://roboraptor.24.hu/2015/12/14/keressuk-magyarorszag-legnagyobb-star-wars-fanjat/']

LINK_FILTER_SUBSTRINGS_SPEC = re.compile('|'.join(['LINK_FILTER_DUMMY_STRING']))

MULTIPAGE_URL_END = re.compile(r'^\b$')  # Dummy


def next_page_of_article_spec(_):
    return None
