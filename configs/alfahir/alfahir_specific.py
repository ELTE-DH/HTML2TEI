#!/usr/bin/env python3
# -*- coding: utf-8, vim: expandtab:ts=4 -*

import re

from html2tei import parse_date, BASIC_LINK_ATTRS, decompose_listed_subtrees_and_mark_media_descendants, tei_defaultdict

PORTAL_URL_PREFIX = 'https://alfahir.hu'

ARTICLE_ROOT_PARAMS_SPEC = [(('div',), {'class': 'region region-content'})]

HTML_BASICS = {'p', 'h2', 'h3', 'h4', 'h5', 'em', 'i', 'b', 'strong', 'mark', 'u', 'sub', 'sup', 'del', 'strike',
               'ul', 'ol', 'li', 'table', 'tr', 'td', 'th', 'quote', 'figure', 'iframe', 'script', 'noscript'}

SOURCE_LIST = ['Alfahír']


def get_meta_from_articles_spec(tei_logger, url, bs):
    data = tei_defaultdict()
    data['sch:url'] = url

    article_root = bs.find('div', class_='article-content-elements')
    percrol_root = bs.find('div', class_='group-right')
    author_root = bs.find('div', class_='field--items')
    tag_root = bs.find('div', class_='field field--name-field-tags'
                                     ' field--type-entity-reference field--label-hidden field--items')

    if article_root is not None:
        if percrol_root is not None:
            perc_h4_title = bs.find_all('h4', class_='esemeny-title')
            perc_h4_author_source = list(set(bs.find_all('h4')) - set(perc_h4_title))
            if perc_h4_author_source is not None:
                perc_author_source_list = list(dict.fromkeys([t.text.strip() for t in perc_h4_author_source]))
                if perc_author_source_list is not None:
                    perc_source_list = set(perc_author_source_list).intersection(SOURCE_LIST)
                    data['sch:author'] = list(set(perc_author_source_list) - set(perc_source_list))
                    if len(perc_source_list) > 0:
                        data['sch:source'] = perc_source_list
            else:
                tei_logger.log('WARNING', f'{url}: AUTHOR / SOURCE TAG NOT FOUND!')

        date_tag = bs.find('div', class_='article-dates')
        if date_tag is not None:
            date_text = date_tag.text.strip()
            if date_text is not None:
                data['sch:datePublished'] = parse_date(date_text.replace(' |', ''), '%Y. %B %d. %H:%M')
            else:
                tei_logger.log('WARNING', f'{url}: DATE FORMAT ERROR!')
        else:
            tei_logger.log('WARNING', f'{url}: DATE TAG NOT FOUND!')

        title = bs.find('h1', class_='page-title')
        if title is not None:
            data['sch:name'] = title.text.strip()
        else:
            tei_logger.log('WARNING', f'{url}: TITLE TAG NOT FOUND!')

        if author_root is not None:
            author_list = [t.text.strip() for t in author_root.find_all('h4')]
            if author_list is not None:
                data['sch:author'] = author_list
        else:
            tei_logger.log('DEBUG', f'{url}: AUTHOR TAG NOT FOUND!')

        if tag_root is not None:
            keywords_list = [t.text.strip() for t in tag_root.find_all('a')]
            if len(keywords_list) > 0:
                data['sch:keywords'] = keywords_list
        else:
            tei_logger.log('DEBUG', f'{url}: TAGS NOT FOUND!')

        source_in_text_1 = article_root.find(
            'div', class_='field field--name-field-forras field--type-string field--label-inline')
        if source_in_text_1 is not None:
            data['sch:source'] = source_in_text_1.find('div', class_='field--item').text.strip()
        else:
            if len(article_root.find_all('p')) > 0:
                source_in_text_2 = article_root.find_all('p')[-1].text.strip()
                if len(source_in_text_2) > 0:
                    if source_in_text_2[0] == '(' and source_in_text_2[-1] == ')':
                        data['sch:source'] = source_in_text_2[1:-1]
                    elif ' - ' in source_in_text_2:
                        if len(source_in_text_2) < 40:
                            data['sch:source'] = source_in_text_2.strip()
                    else:
                        if len(source_in_text_2) < 40:
                            data['sch:source'] = source_in_text_2.strip()
                else:
                    source_in_text_3 = article_root.find('div', class_='field field--name-body field--type-text-with-'
                                                                       'summary field--label-hidden field--item')
                    if source_in_text_3 is not None and len(article_root.find_all('p')) == 3:
                        source_in_text_4 = article_root.find_all('p')[-2].text.strip()
                        if len(source_in_text_4) < 40:
                            data['sch:source'] = source_in_text_4.strip()
                    elif source_in_text_3 is not None and 0 < len(article_root.find_all('p')) < 3:
                        source_in_text_4 = article_root.find_all('p')[-1].text.strip()
                        if len(source_in_text_4) < 40:
                            data['sch:source'] = source_in_text_4.strip()
            else:
                tei_logger.log('WARNING', f'{url}: SOURCE TAG NOT FOUND!')
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
DECOMP = [(('div',), {'class': 'field field-name-field-media-index-foto-video'}),
          (('div',), {'class': 'field field--name-dynamic-token-fieldnode-fb-buttons field--type-ds'
                               ' field--label-hidden field--item'}),
          (('div',), {'class': 'field field--name-dynamic-copy-fieldnode-fb-buttons2 field--type-ds'
                               ' field--label-hidden field--item'}),
          (('div',), {'class': 'field field--name-dynamic-token-fieldnode-minute-html-hook'
                               ' field--type-ds field--label-hidden field--item'}),
          (('div',), {'class': 'field field--name-dynamic-block-fieldnode-legolvasottabbak'
                               ' field--type-ds field--label-above'}),
          (('div',), {'class': 'advert_block advert_wrapper advert_mobile mobiladvert4'}),
          (('div',), {'class': 'advert_block advert_wrapper leaderboard2 advert_dektop'}),
          (('div',), {'class': 'article-content-authors'}),
          (('div',), {'class': 'article-footer'}),
          (('div',), {'class': 'article-dates'}),
          (('div',), {'class': 'group-header'}),
          (('div',), {'class': 'group-footer'}),
          (('div',), {'class': 'view-header'}),
          (('div',), {'class': 'group-left'}),
          (('div',), {'class': 'fb-like'}),
          (('h4',), {'class': 'esemeny-title'}),
          (('noscript',), {}),
          (('section',), {}),
          (('script',), {}),
          (('ins',), {})]

LINK_FILTER_SUBSTRINGS_SPEC = re.compile('|'.join(['LINK_FILTER_DUMMY_STRING']))
MEDIA_LIST = [(('img',), {}),
              (('iframe',), {}),
              (('figure',), {}),
              (('blockquote',), {'class': 'embedly-card'}),
              (('div',), {'class': 'fb-page fb_iframe_widget'}),
              (('div',), {'class': 'video-embed-field-provider-youtube video-embed-field-responsive-video form-group'})]


def decompose_spec(article_dec):
    decompose_listed_subtrees_and_mark_media_descendants(article_dec, DECOMP, MEDIA_LIST)
    return article_dec


BLACKLIST_SPEC = ['https://alfahir.hu/horthy_miklos_utcat_avatnak_kunhegyesen']

MULTIPAGE_URL_END = re.compile(r'^\b$')  # Dummy


def next_page_of_article_spec(_):
    return None
