#!/usr/bin/env python3
# -*- coding: utf-8, vim: expandtab:ts=4 -*

import re

from html2tei import parse_date, BASIC_LINK_ATTRS, decompose_listed_subtrees_and_mark_media_descendants, tei_defaultdict

PORTAL_URL_PREFIX = 'https://kuruc.info'

ARTICLE_ROOT_PARAMS_SPEC = [(('div',), {'class': 'cikktext gallery', 'itemprop': 'articleBody'}),
                            ]

HTML_BASICS = {'p', 'h3', 'h2', 'h4', 'h5', 'em', 'i', 'b', 'strong', 'mark', 'u', 'sub', 'sup', 'del', 'strike',
               'ul', 'ol', 'li', 'table', 'tr', 'td', 'th', 'quote', 'figure', 'iframe', 'script', 'noscript'}

def get_meta_from_articles_spec(tei_logger, url, bs):
    data = tei_defaultdict()
    data['sch:url'] = url
    
    # MISSING FROM PORTAL: data['sch:dateModified']

    # ARTICLE SECTION
    section_tag = bs.find('attribute', {'name': 'category'})
    if section_tag is not None and 'value' in section_tag.attrs.keys():
        section = section_tag['value']
        if len(section) > 0:
            data['sch:articleSection'] = section
        else:
            tei_logger.log('WARNING', f'{url}: ARTICLE SECTION TAG PARSE ERROR!')
    else:
        tei_logger.log('WARNING', f'{url}: ARTICLE SECTION NOT FOUND!')
    
    article_root = bs.find('div', {'class': 'tblot'})
    if article_root is not None:

        # NAME
        title_tag = article_root.find('div', {'class': 'focikkheader'})
        if title_tag is not None:
            title_text = title_tag.get_text(strip=True)
            if title_text is not None:
                data['sch:name'] = title_text
            else: 
                tei_logger.log('WARNING', f'{url}: TITLE TAG EMPTY!')
        else: 
            tei_logger.log('WARNING', f'{url}: TITLE NOT FOUND IN URL!')

        # AUTHOR / https://kuruc.info/r/6/150707/
        all_paragraphs = article_root.find_all('div', {'class': 'cikktext', 'id':None})
        if len(all_paragraphs) > 0:

            possible_author_tag = all_paragraphs[-1].find('b')
            if possible_author_tag is not None:
                tag_text = possible_author_tag.get_text(strip=True).replace('- Kuruc.info', '').strip()
                split_t = tag_text.split(' ')
                if 1 < len(split_t) <= 3 and ('(' or ')') not in tag_text and all([w[0].isupper() for w in split_t]):
                    data['sch:author'] = tag_text
                else:
                    tei_logger.log('DEBUG', f'{url}: AUTHOR TAG EMPTY!')
            else:
                tei_logger.log('DEBUG', f'{url}: AUTHOR TAG NOT FOUND!')

        # KEYWORDS and DATE PUBLISHED
        meta_header = article_root.find('p', {'class': 'cikkdatum'})
        if meta_header is not None:
            
            # keywords
            a_tags = meta_header.find_all('a', href=re.compile('/t/[0-9]'))
            if len(a_tags) > 0:
                data['sch:keywords'] = [t.get_text(strip=True) for t in a_tags if len(t.get_text(strip=True)) > 0]
            else:
                tei_logger.log('INFO', f'{url}: KEYWORDS NOT FOUND!')
                
            # datePublished
            date_published_tag = meta_header.find('span', {'itemprop': "datePublished"})
            if date_published_tag is not None:
                date_published_raw = date_published_tag.get_text(strip=True)
                if date_published_raw is not None:
                    data['sch:datePublished'] = parse_date(date_published_raw, "%Y. %B %d. %H:%M")
                else: 
                    tei_logger.log('WARNING', f'{url}: DATE FORMAT ERROR!')
            else: 
                tei_logger.log('WARNING', f'{url}: DATE TAG NOT FOUND!')
            
        else:
            tei_logger.log('WARNING', f'{url}: META HEADER [datePublished, keywords] NOT FOUND!')

    else:
        tei_logger.log('WARNING', f'{url}: ARTICLE ROOT NOT FOUND!')


    return data


def excluded_tags_spec(tag):
    return tag


BLOCK_RULES_SPEC = {}
BIGRAM_RULES_SPEC = {}  
# a spec-et lehet kéne kezelni - amikor <dic class=cikktext> direkt
# leszármazottja akkor lehet címsornak
# és ha <b> tag van cikktexben egyedül akkor lehet vez_bekezd

# néhol csak ömlesztve van a szöveg sé <br>-ek választják el a paragrafusokat
# lásd: https://kuruc.info/r/9/219243/   https://kuruc.info/r/1/524/

# Egy ilyet lehet akárhogy feldolgozni? https://kuruc.info/r/1/18437

# hogy viselkedik a beagyazott tartalom a social media-val ? https://kuruc.info/r/2/150191

# <span class=cikklead> ebben nem lehet megbízni! 

LINKS_SPEC = {}
DECOMP = []
MEDIA_LIST = []


def decompose_spec(article_dec):
    decompose_listed_subtrees_and_mark_media_descendants(article_dec, DECOMP, MEDIA_LIST)
    return article_dec


BLACKLIST_SPEC = []
LINK_FILTER_SUBSTRINGS_SPEC = re.compile('|'.join(['LINK_FILTER_DUMMY_STRING']))

MULTIPAGE_URL_END = re.compile(r'^\b$')  # Dummy


def next_page_of_article_spec(_):
    return None
