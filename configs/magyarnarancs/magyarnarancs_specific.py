#!/usr/bin/env python3
# -*- coding: utf-8, vim: expandtab: ts=4 -*

import re

from html2tei import parse_date, BASIC_LINK_ATTRS, decompose_listed_subtrees_and_mark_media_descendants, tei_defaultdict

PORTAL_URL_PREFIX = 'https://magyarnarancs.hu/'

ARTICLE_ROOT_PARAMS_SPEC = [(('div',), {'class': 'card-body'})]

HTML_BASICS = {'p', 'h3', 'h2', 'h4', 'h5', 'em', 'i', 'b', 'strong', 'mark', 'u', 'sub', 'sup', 'del', 'strike',
               'ul', 'ol', 'li', 'table', 'tr', 'td', 'th', 'quote', 'figure', 'iframe', 'script', 'noscript'}

SOURCE = ['narancs.hu', 'narancs. hu', 'narancs hu', 'narancs', 'narancs.', 'narancs.h',
          'Narancs', 'Narancsfül', 'narancsfül', 'narancsszem', 'Magyar Narancs', 'narancsblog', 'MTI/narancs.hu',
          'Narancs.hu/MTI', 'narancs.hu/MTI', 'narancs.hu/M', 'Narancs.hu/MT', 'narancs.hu-MTI', 'MTI',
          'Narancs-összeállítás', 'narancs.hu-összeállítás', 'narancs.hu/Markó Anita', 'szegeder.hu/narancs.hu',
          'TASZ/narancs.hu', 'narancs.hu/Amnesty', 'narancs.hu/Telex', 'media1.hu/narancs.hu', 'narancs.hu/HVG',
          'narancs.hu/Guardian', 'narancs.hu/Szabad ország', 'narancs.hu/MTA', 'Reuters/narancs.hu',
          'Narancs.hu/MTI/OS', 'narancs.hu/Police.hu', 'Police.hu', 'Fizetett tartalom',
          'narancs.hu/Republikon', 'MTI/narancs', 'narancs hu.', 'MTI/Világgazdaság/narancs.hu', 'narancs.hu - B. T.',
          'transindex.ro', 'MTI-OS', 'nrancs.hu']


def get_meta_from_articles_spec(tei_logger, url, bs):
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
        author_or_source = [t.text.strip() for t in meta_root.find_all('span', class_='author-name')]
        author_list, source_list = [], []
        [source_list.append(creator) if creator in SOURCE else author_list.append(creator) for creator in
         author_or_source]
        if len(author_list) > 0 or len(source_list) > 0:
            author_list_corr = []
            if len(author_list) > 0:
                for auth in author_list:
                    if ',' in auth:
                        author_list_corr.extend(one_author.strip() for one_author in auth.split('\''))
                    else:
                        author_list_corr.append(auth)
                data['sch:author'] = author_list_corr
            if len(source_list) > 0:
                data['sch:source'] = source_list
        else:
            tei_logger.log('DEBUG', f'{url}: AUTHOR / SOURCE TAG NOT FOUND!')
        if tag_root is not None:
            keywords_list = [t.text.strip() for t in tag_root.find_all('a')]
            if len(keywords_list) > 0:
                data['sch:keywords'] = keywords_list
        else:
            tei_logger.log('DEBUG', f'{url}: TAGS NOT FOUND!')
        return data
    else:
        tei_logger.log('WARNING', f'{url}: META ROOT NOT FOUND (UNKNOWN ARTICLE SCHEME)!')
        return None


def excluded_tags_spec(tag):
    # if tag.name not in HTML_BASICS:
    #     tag.name = 'else'
    # tag.attrs = {}
    return tag


BLOCK_RULES_SPEC = {}
BIGRAM_RULES_SPEC = {'table_text': {('media_hivatkozas', 'det_by_any_desc'): ('media_tartalom', 'media_hivatkozas')},
                    'lista': {('media_hivatkozas', 'det_by_any_desc'): ('to_unwrap', 'media_hivatkozas')},
                    'listaelem': {('media_hivatkozas', 'det_by_any_desc'): ('to_unwrap', 'media_hivatkozas')},
                    'kiemelt': {('media_hivatkozas', 'det_by_any_desc'): ('to_unwrap', 'media_hivatkozas')}
                    }

LINKS_SPEC = BASIC_LINK_ATTRS
DECOMP = [(('div',), {'class': 'banner-wrapper bgr mb-2 mt-2'}),
          (('div',), {'class': 'blockquote orange'}),
          (('div',), {'class': 'fb-like mb-4'}),
          (('div',), {'class': 'banner-wrapper'}),
          (('h1',), {'class': 'card-title'}),
          (('ul',), {'class': 'tags my-5'}),
          (('div',), {'class': 'card-info'}),
          (('div',), {'class': 'share-box'}),
          (('div',), {'class': 'fb-like'}),
          (('div',), {'class': 'wrap'}),
          (('script',), {})]

MEDIA_LIST = [(('div',), {'class': 'image image-div inner'}),
              (('div',), {'data-blocktype': 'Cikk_Oldal_Embed'}),
              (('div',), {'class': 'inner-cikkbox cikkbox-img align-left'})
              # (('table',), {})
              ]


def decompose_spec(article_dec):
    decompose_listed_subtrees_and_mark_media_descendants(article_dec, DECOMP, MEDIA_LIST)
    return article_dec


BLACKLIST_SPEC = ['https://magyarnarancs.hu/film2/kinn-az orosz-vadonban-a-jegmezok-lova-national-geographic-83800',
                  'https://magyarnarancs.hu/belpol/orban-merkel talalkozo-kiegyeznek-dontetlenben-93514',
                  'https://magyarnarancs.hu/egotripp/-75067']


_filter_link_list = ['https://w.soundcloud.com/player/?url=https  %3A//api.soundcloud.com/tracks/173157757&colo  r=ff5500&auto_play=false&hide_related=fal  se&show_comments=true&show_user=true&  show_reposts=false',
                     'https://w.soundcloud.com/player/?url=https  %3A//api.soundcloud.com/tracks/173157758&colo  r=ff5500&auto_play=false&hide_related=fal  se&show_comments=true&show_user=true&  show_reposts=false',
                     'https://w.soundcloud.com/player/?url=https  %3A//api.soundcloud.com/tracks/173157759&colo  r=ff5500&auto_play=false&hide_related=fal  se&show_comments=true&show_user=true&  show_reposts=false',
                     'https://w.soundcloud.com/player/?url=https  %3A//api.soundcloud.com/tracks/173157761&colo  r=ff5500&auto_play=false&hide_related=fal  se&show_comments=true&show_user=true&  show_reposts=false',
                     'https://w.soundcloud.com/player/?url=https  ://api.soundcloud.com/tracks/173157759&amp;colo  r=ff5500&amp;auto_pl$y=false&amp;hide_related=fal  se&amp;show_comments=true&amp;show_user=true&amp;  show_reposts=false" rend="embedded_content" resp="script" type="corrected',
                     'https://w.soundcloud.com/player/?url=https  ://api.soundcloud.com/tracks/173157759&amp;colo  r=ff5500&amp;auto_play=false&amp;hide_related=fal  se&amp;show_comments=true&amp;show_user=true&amp;  show_reposts=false" rend="embedded_content" resp="script" type="corrected',
                     'http://www.blikk.hu/sztarvilag/sztarsztorik/demjen-rozsi-akos-meg-finoman-is-fogalmazott-a-nokrol/d717vjs :']
LINK_FILTER_SUBSTRINGS_SPEC = re.compile('|'.join([re.escape(l) for l in _filter_link_list]))

                                                   
MULTIPAGE_URL_END = re.compile(r'^\b$')  # Dummy


def next_page_of_article_spec(_):
    return None
