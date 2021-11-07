#!/usr/bin/env python3
# -*- coding: utf-8, vim: expandtab: ts=4 -*

import re

from html2tei import parse_date, BASIC_LINK_ATTRS, decompose_listed_subtrees_and_mark_media_descendants, tei_defaultdict

PORTAL_URL_PREFIX = 'https://magyarnarancs.hu/'

ARTICLE_ROOT_PARAMS_SPEC = [(('div',), {'class': 'card-body'})]

HTML_BASICS = {'p', 'h3', 'h2', 'h4', 'h5', 'em', 'i', 'b', 'strong', 'mark', 'u', 'sub', 'sup', 'del', 'strike',
               'ul', 'ol', 'li', 'table', 'tr', 'td', 'th', 'quote', 'figure', 'iframe', 'script', 'noscript'}

AUTH_SOURCE = {'narancs.hu', 'narancs hu', 'narancs', 'narancsblog', 'MTI/narancs.hu', 'narancs.hu/MTI',
               'narancs.hu-MTI', 'MTI', 'narancs.hu/Police.hu', 'Police.hu', 'Fizetett tartalom'}


def get_meta_from_articles_spec(tei_logger, url, bs, auth_source=AUTH_SOURCE):
    data = tei_defaultdict()
    data['sch:url'] = url
    meta_root = bs.find('div', class_='card-info')
    tag_root = bs.find('ul', class_='tags my-5')
    if meta_root is not None:
        # The portal does NOT store the dates consequently.
        # The webpage uses different HTML structure for storing the date of the articles:
        # - the articles coming from the offline version of MagyarNarancs, and
        # - the online articles have different HTML structures to store the date metadata.
        date_tag_list = meta_root.find_all('li')
        # Checking for the articles coming from MagyarNarancs (offline version)
        if '/lapszamok/' in str(date_tag_list):
            if len(date_tag_list) == 2:
                # Saving the relevant date_tag from the date_tag_list
                date_tag = date_tag_list[0]
            else:
                # Checking for the author in the relevant element of the date_tag_list
                if 'szerzo' in str(date_tag_list[1]):
                    # Saving the relevant date_tag from the date_tag_list
                    date_tag = date_tag_list[2]
                else:
                    # Saving the relevant date_tag from the date_tag_list
                    date_tag = meta_root.find_all('li')[1]
        else:
            date_tag = meta_root.find_all('li')[-1]
        if date_tag is not None:
            date_text = date_tag.text.strip()
            if date_text is not None:
                data['sch:datePublished'] = parse_date(date_text, '%Y.%m.%d %H:%M')
            else:
                tei_logger.log('WARNING', f'{url}: DATE FORMAT ERROR!')
        else:
            tei_logger.log('WARNING', f'{url}: DATE TAG NOT FOUND!')
        section_tag = meta_root.find('h4', class_='card-topic')
        if section_tag is not None:
            data['sch:articleSection'] = section_tag.text.strip()
        else:
            tei_logger.log('WARNING', f'{url}: SECTION TAG NOT FOUND!')
        title = bs.find('h1', class_='card-title')
        if title is not None:
            data['sch:name'] = title.text.strip()
        else:
            tei_logger.log('WARNING', f'{url}: TITLE TAG NOT FOUND!')
        subtitle = bs.find('h3', class_='card-subtitle')
        if subtitle is not None:
            data['sch:alternateName'] = subtitle.text.strip()
        author_list = [t.text.strip() for t in meta_root.find_all('span', class_='author-name') if
                       t.text.strip() not in auth_source]
        source_list = [t.text.strip() for t in meta_root.find_all('span', class_='author-name') if
                       t.text.strip() in auth_source]
        if len(author_list) > 0 or len(source_list) > 0:
            if len(author_list) > 0:
                data['sch:author'] = author_list
            if len(source_list) > 0:
                data['sch:source'] = source_list
        else:
            tei_logger.log('WARNING', f'{url}: AUTHOR / SOURCE TAG NOT FOUND!')
        if tag_root is not None:
            keywords_list = [t.text.strip() for t in tag_root.find_all('a')]
            if len(keywords_list) > 0:
                data['sch:keywords'] = keywords_list
        else:
            tei_logger.log('DEBUG', f'{url}: TAGS NOT FOUND!')
        return data
    else:
        tei_logger.log('WARNING', f'{url}: ARTICLE BODY NOT FOUND OR UNKNOWN ARTICLE SCHEME!')
        return None


def excluded_tags_spec(tag):
    if tag.name not in HTML_BASICS:
        tag.name = 'else'
    tag.attrs = {}
    return tag


BLOCK_RULES_SPEC = {}
BIGRAM_RULES_SPEC = {}
LINKS_SPEC = BASIC_LINK_ATTRS
DECOMP = [(('div',), {'class': 'blockquote orange'}),
          (('div',), {'class': 'banner-wrapper'}),
          (('div',), {'class': 'share-box'}),
          (('div',), {'class': 'fb-like'}),
          (('div',), {'class': 'wrap'}),
          (('script',), {})]

MEDIA_LIST = [(('div',), {'class': 'image image-div inner'}),
              (('div',), {'data-blocktype': 'Cikk_Oldal_Embed'}),
              (('div',), {'class': 'inner-cikkbox cikkbox-img align-left'}),
              (('table',), {})]


def decompose_spec(article_dec):
    decompose_listed_subtrees_and_mark_media_descendants(article_dec, DECOMP, MEDIA_LIST)
    return article_dec


BLACKLIST_SPEC = ['https://magyarnarancs.hu/film2/kinn-az orosz-vadonban-a-jegmezok-lova-national-geographic-83800',
                  'https://magyarnarancs.hu/belpol/orban-merkel talalkozo-kiegyeznek-dontetlenben-93514']

LINK_FILTER_SUBSTRINGS_SPEC = re.compile('|'.join(['LINK_FILTER_DUMMY_STRING']))

MULTIPAGE_URL_END = re.compile(r'^\b$')  # Dummy


def next_page_of_article_spec(_):
    return None
