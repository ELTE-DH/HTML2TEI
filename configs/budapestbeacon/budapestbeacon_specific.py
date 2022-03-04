#!/usr/bin/env python3
# -*- coding: utf-8, vim: expandtab:ts=4 -*
import json

from bs4 import BeautifulSoup
import re
from os.path import join as os_path_join, dirname as os_path_dirname, abspath as os_path_abspath
from html2tei import parse_date, BASIC_LINK_ATTRS, decompose_listed_subtrees_and_mark_media_descendants, tei_defaultdict

PORTAL_URL_PREFIX = 'https://budapestbeacon.com'

ARTICLE_ROOT_PARAMS_SPEC = [(('div',), {'id': 'primary'})]  # [(('main',), {'class': 'post-main'})]


def get_meta_from_articles_spec(tei_logger, url, bs):
    # <span class="posted-on">8:47, 12.04.2017</span>
    # <span class="byline"> - Lestyánszky Ádám</span>
    # <p class="posted-on-line">

    data = tei_defaultdict()
    data['sch:url'] = url
    if bs.html.attrs['lang'] == 'en-US':
        data['sch:inLanguage'] = 'en-US'
    parsed_mod_date = None
    date_tag = bs.find('meta', {'property': 'article:published_time'})
    date_mod_tag = bs.find('meta', {'property': 'article:modified_time'})
    if date_mod_tag is not None and 'content' in date_mod_tag.attrs.keys():
        parsed_mod_date = parse_date(date_mod_tag.attrs['content'][:19], '%Y-%m-%dT%H:%M:%S')
        data['sch:dateModified'] = parsed_mod_date
    if date_tag is not None and 'content' in date_tag.attrs.keys():
        parsed_date = parse_date(date_tag.attrs['content'][:19], '%Y-%m-%dT%H:%M:%S')
        data['sch:datePublished'] = parsed_date
    else:
        if parsed_mod_date is not None:
            data['sch:datePublished'] = parsed_mod_date
        else:
            meta_script_tag_text = bs.find('script', {'type': 'application/ld+json'}).get_text(strip=True)
            if meta_script_tag_text is not None:
                meta_json = json.loads(meta_script_tag_text)
                if '@graph' in meta_json.keys():
                    date_pub = meta_json["@graph"][-1]["datePublished"]
                else:
                    date_pub = meta_json["datePublished"]
                if date_pub is not None:
                    parsed_pub_date = parse_date(date_pub[:19], '%Y-%m-%dT%H:%M:%S%z')
                    if parsed_pub_date is not None:
                        data['sch:datePublished'] = parsed_pub_date
                    else:
                        tei_logger.log('DEBUG', f'{url}: PUBLICATION DATE FORMAT ERROR!')
                else:
                    tei_logger.log('DEBUG', f'{url}: PUBLICATION DATE NOT FOUND!')

                meta_json = json.loads(meta_script_tag_text)
                if '@graph' in meta_json.keys():
                    date_modified = meta_json["@graph"][-1]["dateModified"]
                else:
                    date_modified = meta_json["dateModified"]
                if date_modified is not None:
                    parsed_modification_date = parse_date(date_modified[:19], '%Y-%m-%dT%H:%M:%S%z')
                    if parsed_modification_date is not None:
                        data['sch:dateModified'] = parsed_modification_date
                    else:
                        tei_logger.log('DEBUG', f'{url}: MODIFICATION DATE FORMAT ERROR!')
                else:
                    tei_logger.log('DEBUG', f'{url}: MODIFICATION DATE NOT FOUND!')

    title = bs.find('h2', class_='post-heading')
    if title:
        data['sch:name'] = title.text.strip()
    else:
        tei_logger.log('WARNING', f'{url}: TITLE NOT FOUND IN URL!')
    author_tag = bs.find('a', rel='author')
    if author_tag is not None:
        data['sch:author'] = [author_tag.text.strip()]
    else:
        author_tag2 = bs.find('span', class_='byline')
        if author_tag2 is not None:
            data['sch:author'] = [author_tag2.text.strip()]
        else:
            meta_script_tag_text = bs.find('script', {'type': 'application/ld+json'}).get_text(strip=True)
            json_author = json.loads(meta_script_tag_text)['author']
            if json_author:
                data['sch:author'] = [json_author['name']]
            else:
                tei_logger.log('WARNING', f'{url}: AUTHOR TAG NOT FOUND!')
    return data


def excluded_tags_spec(tag):
    if tag.name == 'a':
        for k in tag.attrs.keys():
            if 'noopener' in tag.attrs[k] and 'noreferrer' in tag.attrs[k]:
                tag.attrs[k] = '@noopener'
                """“nofollow” noopener noreferrer"""
    return tag


BLOCK_RULES_SPEC = {}
BIGRAM_RULES_SPEC = {}
LINKS_SPEC = BASIC_LINK_ATTRS
DECOMP = []
MEDIA_LIST = []


def decompose_spec(article_dec):
    decompose_listed_subtrees_and_mark_media_descendants(article_dec, DECOMP, MEDIA_LIST)
    for f in reversed(article_dec.find_all()):
        if 'Amennyiben tetszett a cikkünk' in f.text:
            print(f)
            f.decompose()
            break
    return article_dec


BLACKLIST_SPEC = [url.strip() for url in
                  open(os_path_join(os_path_dirname(os_path_abspath(__file__)),
                                    'budapestbeacon_BLACKLIST.txt')).readlines()]

LINK_FILTER_SUBSTRINGS_SPEC = re.compile('|'.join(['LINK_FILTER_DUMMY_STRING']))

MULTIPAGE_URL_END = re.compile(r'^\b$')  # Dummy


def next_page_of_article_spec(_):
    return None
