#!/usr/bin/env python3
# -*- coding: utf-8, vim: expandtab:ts=4 -*-

import re
from os.path import join as os_path_join, dirname as os_path_dirname, abspath as os_path_abspath

from html2tei import parse_date, decompose_listed_subtrees_and_mark_media_descendants, tei_defaultdict

PORTAL_URL_PREFIX = 'https://vs.hu'

ARTICLE_ROOT_PARAMS_SPEC = [(('div',), {'itemprop': 'articleBody'})]


def author_source_norm(extracted_meta):
    # SPEC VS.HU
    ret_list = []
    if isinstance(extracted_meta, list):
        for meta in extracted_meta:
            ret_list.extend([m.strip() for m in re.split(',|/|– |;| és ', meta) if len(m.strip()) > 0])
        return ret_list
    return [m.strip() for m in re.split(',|/|– |;| és ', extracted_meta) if len(m.strip())>0]


def get_meta_from_articles_spec(tei_logger, url, bs):
    data = tei_defaultdict()
    data['sch:url'] = url
    meta_root = bs.find('section', class_='article')
    if meta_root is not None:
        date_tag = bs.find('span', class_='date')
        if date_tag is not None:
            parsed_date = parse_date(date_tag.text.strip(), '%Y. %B %d., %A %H:%M')
            if parsed_date is not None:
                data['sch:datePublished'] = parsed_date
            else:
                tei_logger.log('WARNING', f'{url}: DATE FORMAT ERROR!')
        else:
            tei_logger.log('WARNING', f'{url}: DATE TAG NOT FOUND!')
        title = meta_root.find('h1', itemprop='headline')
        if title is not None:
            data['sch:name'] = title.text.strip().replace('/t', ' ')
        else:
            tei_logger.log('WARNING', f'{url}: TITLE TAG NOT FOUND!')
        author_tag = meta_root.find('span', itemprop='author')
        if author_tag is not None:  # MTI/VS.hu": 704
            author_text = author_tag.text.strip()
            creatorlist = author_source_norm(author_text)
            if len(creatorlist) > 1:
                data['originalAuthorString'] = [author_text]
            # https://vs.hu/sport/osszes/magyarorszag-spanyolorszag-percrol-percre-1211#!s184
            authorlist = []
            sourcelist = []
            [sourcelist.append(au.strip()) if 'MTI' in au.strip() else authorlist.append(au.strip()) for au in creatorlist]
            if len(sourcelist) > 0:
                data['sch:source'] = sourcelist
            if len(authorlist) > 0:
                data['sch:author'] = authorlist
        else:
            tei_logger.log('DEBUG', f'{url}: AUTHOR TAG NOT FOUND!')
        keywords_list = [t.text.strip() for t in meta_root.find_all('a', class_='tag')]
        if len(keywords_list) > 0:
            data['sch:articleSection'] = keywords_list[0]
            if len(keywords_list) > 1:
                data['subsection'] = keywords_list[1]
            if len(keywords_list) > 2:
                data['sch:keywords'] = keywords_list[2:]
        else:
            tei_logger.log('WARNING', f'{url}: SUBJECT TAG NOT FOUND!')
        return data
    else:
        tei_logger.log('WARNING', f'{url}: ARTICLE BODY NOT FOUND OR UNKNOWN ARTICLE SCHEME!')
        return None


def excluded_tags_spec(tag):
    tag_attrs = tag.attrs
    if tag.name == 'a' and tag.has_attr('rel'):
        for multi_attrs in tag_attrs['rel']:    # multi-valued, de csak az érték egy részére kell illeszkednie
            if 'wp-att' in multi_attrs:
                tag_attrs['rel'] = '@wp-att'
                break
    if tag.name == 'div' and tag.has_attr('data-youtube'):
        tag_attrs['data-youtube'] = '@ALNUM'    # a multi listát át tudja írni erre a sztringre?
    for atr in tag_attrs:
        if atr == 'class' and atr[0].startswith('yiv'):
            atr[0] = '@yiv'
    if 'table' == tag.name:
        tag.attrs = {}
    return tag


BLOCK_RULES_SPEC = {'idezet': {'rename': {'idezet': 'to_unwrap', 'cimsor': 'felkover', 'idezojel': 'to_unwrap'}},
                    'doboz': {'rename': {'cimsor': 'cimsor'}},
                    'galeria': {'rename': {'media_hivatkozas': 'caption'}}}
BIGRAM_RULES_SPEC = {}  # 'embed_div': {'caption': ('caption', 'to_unwrap', 'det_by_any_desc')}}
LINKS_SPEC = {'a', '0_MDESC_a', 'img', '0_MDESC_img', 'iframe', '0_MDESC_meta', 'div'}

DECOMP = [(('script',), {}),
          (('div',), {'class': 'avcode'}),
          (('div',), {'class': ['goAdverticum', 'ajax_zone', 'richmedia_container', 'articlebottom']}),
          (('div',), {'class': 'banner_placeholder'}),
          (('div',), {'class': 'opinion'}),
          (('span',), {'class': 'apple-converted-space'}),
          (('span',), {'class': 'Apple-converted-space'})
          ]
MEDIA_LIST = [(('figure',), {}),
              (('div',), {'class': 'gallery_item'}),
              (('iframe',), {}),
              (('div',), {'class': 'fb-video'}),
              (('div',), {'class': 'fb-post'}),
              (('blockquote',), {'class': 'instagram-media'}),
              (('blockquote',), {'class': 'twitter-tweet'})]


def decompose_spec(article_dec):
    decompose_listed_subtrees_and_mark_media_descendants(article_dec, DECOMP, MEDIA_LIST)
    for d in reversed(article_dec.find_all()):
        """reversed: azért hogy a legszűkebb tartományból induljon, és ne töröljön olyan szöveget,
        ami a törlendő alatt van, de azonos tartományban"""
        if d.text == 'Create infographics':
            d.decompose()
    for d in article_dec.find_all():
        if d.text.strip().startswith('Korábbi Buksza-posztok:') or \
                d.text.strip().startswith('Ha tetszett a poszt, a Bukszát'):
            d.decompose()
    return article_dec


BLACKLIST_SPEC = [url.strip() for url in open(os_path_join(os_path_dirname(os_path_abspath(__file__)),
                                                           'vs_BLACKLIST.txt')).readlines()]
LINK_FILTER_SUBSTRINGS_SPEC = re.compile('|'.join(['LINK_FILTER_DUMMY_STRING']))

MULTIPAGE_URL_END = re.compile(r'^\b$')  # Dummy


def next_page_of_article_spec(_):
    return None
