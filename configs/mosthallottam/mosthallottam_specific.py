#!/usr/bin/env python3
# -*- coding: utf-8, vim: expandtab:ts=4 -*-

import re

from html2tei import parse_date, decompose_listed_subtrees_and_mark_media_descendants, tei_defaultdict

PORTAL_URL_PREFIX = 'https://www.mosthallottam.hu'

ARTICLE_ROOT_PARAMS_SPEC = [(('div',), {'class': 'entry-inner'})]


def get_meta_from_articles_spec(tei_logger, url, bs):
    data = tei_defaultdict()
    data['sch:url'] = url
    article_root = bs.find('div', class_='post-inner group')
    if article_root is not None:
        date_tag = article_root.find('time', class_='published')
        if date_tag is not None and 'datetime' in date_tag.attrs.keys():
            parsed_date = parse_date(date_tag.attrs['datetime'][0:19], '%Y-%m-%dT%H:%M:%S')
            data['sch:datePublished'] = parsed_date
        else:
            tei_logger.log('WARNING', f'{url}: DATE FORMAT ERROR!')
        mod_date_tag = article_root.find('time', class_='updated')
        if mod_date_tag is not None and 'datetime' in mod_date_tag.attrs.keys():
            parsed_mod_date = parse_date(mod_date_tag.attrs['datetime'][0:19], '%Y-%m-%dT%H:%M:%S')
            data['sch:dateModified'] = parsed_mod_date
        title = article_root.find('h1', class_='post-title')
        if title is not None:
            data['sch:name'] = title.text.strip()
        else:
            tei_logger.log('WARNING', f'{url}: TITLE NOT FOUND IN URL!')
        author = article_root.find('a', rel='author')
        if author is not None:
            data['sch:author'] = [author.text.strip()]
        else:
            tei_logger.log('WARNING', f'{url}: AUTHOR TAG NOT FOUND!')
        section_tag = bs.find('li', class_='category')
        if section_tag is not None:
            data['sch:articleSection'] = section_tag.text.strip()
        else:
            tei_logger.log('WARNING', f'{url}: SECTION TAG NOT FOUND!')

        keywords_root = bs.find('p', class_='post-tags')
        if keywords_root is not None:
            article_tags = [a.text.strip() for a in keywords_root.find_all('a', rel='tag') if a is not None]
            if len(article_tags) > 0:
                data['sch:keywords'] = article_tags
        else:
            tei_logger.log('DEBUG', f'{url}: TAGS NOT FOUND!')
        return data
    else:
        tei_logger.log('WARNING', f'{url}: METADATA CONTAINER NOT FOUND!')
        return None


def excluded_tags_spec(tag):
    return tag


BLOCK_RULES_SPEC = {}

BIGRAM_RULES_SPEC = {'hivatkozas': {('media_hivatkozas', 'det_by_child'): ('caption', 'media_hivatkozas')}}

LINKS_SPEC = {'a', '0_MDESC_a', 'img', '0_MDESC_img', 'iframe', 'blockquote'}    # img_data-src

DECOMP = [(('div',), {'class': 'the-champ-sharing-container'}),
          (('div',), {'class': 'quads-location'}),
          (('div',), {'class': 'google-auto-placed ap_container'})]

MEDIA_LIST = []


def decompose_spec(article_dec):
    decompose_listed_subtrees_and_mark_media_descendants(article_dec, DECOMP, MEDIA_LIST)
    return article_dec


BLACKLIST_SPEC = ['https://www.mosthallottam.hu/about/',
                  'https://www.mosthallottam.hu/kapcsolat/',
                  'https://www.mosthallottam.hu/impresszum/',
                  'https://www.mosthallottam.hu/felhasznalasi-feltetel-es-adatvedelem/']

LINK_FILTER_SUBSTRINGS_SPEC = re.compile('|'.join(['LINK_FILTER_DUMMY_STRING']))

MULTIPAGE_URL_END = re.compile(r'^\b$')  # Dummy


def next_page_of_article_spec(_):
    return None
