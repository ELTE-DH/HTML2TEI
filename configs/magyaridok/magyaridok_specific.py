#!/usr/bin/env python3
# -*- coding: utf-8, vim: expandtab:ts=4 -*-

import re

from html2tei import parse_date, decompose_listed_subtrees_and_mark_media_descendants, tei_defaultdict

PORTAL_URL_PREFIX = 'https://www.magyaridok.hu'
ARTICLE_ROOT_PARAMS_SPEC = [(('div',), {'class': 'entry-content'})]
KNOWN_MAIN_COLUMNS = {'Belföld', 'Külföld', 'Sport', 'Vélemény', 'A Helyzet', 'Gazdaság', 'Kultúra', 'Lugas'}


def get_meta_from_articles_spec(tei_logger, url, bs):
    data = tei_defaultdict()
    data['sch:url'] = url
    article_root = bs.find('article')
    if article_root is not None:
        date_tag = bs.find('span', class_='en-article-dates-main')
        if date_tag is not None:  # 2019. augusztus 23. péntek 14:22
            article_date_text = date_tag.text
            parsed_date = parse_date(article_date_text, '%Y. %B %d. %A %H:%M')
            if parsed_date is not None:
                data['sch:datePublished'] = parsed_date
            else:
                tei_logger.log('WARNING', f'{url}: DATE TEXT FORMAT ERROR!')
        else:
            tei_logger.log('WARNING', f'{url}: DATE TAG NOT FOUND!')
        modified_date_tag = bs.find('span', class_='en-article-dates-updated')  # 2018. 05. 09. 07:46
        if modified_date_tag is not None:
            modified_date_text = modified_date_tag.text
            parsed_modified_date = parse_date(modified_date_text, '%Y. %m. %d. %H:%M')
            if parsed_modified_date is not None:
                data['sch:dateModified'] = parsed_modified_date
            else:
                tei_logger.log('WARNING', f'{url}: MODIFIED DATE TEXT FORMAT ERROR!')
        title = article_root.find('div', class_='et_main_title')
        if title is not None:
            article_title = title.find('h1')
            data['sch:name'] = article_title.text.strip()
        else:
            tei_logger.log('WARNING', f'{url}: TITLE NOT FOUND IN URL!')
        subtitle = article_root.find('div', class_='en-article-subtitle')
        if subtitle is not None:
            data['sch:alternateName'] = subtitle.text.strip()
        author = article_root.find('div', class_='en-article-author')
        source = article_root.find('div', class_='en-article-source col-sm')
        if author is not None:
            data['sch:author'] = [author.text.strip()]
        elif source is not None:
            # In case if not an author, only source (MTI)
            data['sch:source'] = source.text.strip()
        else:
            tei_logger.log('WARNING', f'{url}: AUTHOR TAG NOT FOUND!')
        article_tags = []
        section_line = article_root.find('span', class_='en-article-header-column')
        if section_line is not None:
            sections = [a.text for a in section_line.find_all('a') if a is not None]
            for col in sections:
                if col in KNOWN_MAIN_COLUMNS:
                    data['sch:articleSection'] = col
                elif col:
                    article_tags.append(col)
        else:
            tei_logger.log('DEBUG', f'{url}: SECTION TAG NOT FOUND!')

        keywords_root = article_root.find('div', class_='en-article-tags')
        if keywords_root is not None:

            article_tags.extend(a.text.strip() for a in keywords_root.find_all('a', rel='tag') if a is not None)
            data['sch:keywords'] = article_tags
        else:
            tei_logger.log('DEBUG', f'{url}: TAGS NOT FOUND!')

        return data
    else:
        tei_logger.log('WARNING', f'{url}: ARTICLE BODY NOT FOUND!')
        return None


def excluded_tags_spec(tag):
    return tag


BLOCK_RULES_SPEC = {'lista': {'rename': {'vez_bekezdes': 'felkover'},
                              'default': 'listaelem',
                              'not_valid_inner_blocks': ['doboz'],
                              'not_valid_as_outer_for': ['kozvetites', 'vez_bekezdes']
                              }}
BIGRAM_RULES_SPEC = {}
LINKS_SPEC = {'a', '0_MDESC_a', 'img', '0_MDESC_img', 'iframe', '0_MDESC_iframe', 'blockquote', 'div'}
DECOMP = [(('div',), {'class': 'en-article-fb-inline'}),
          (('script',), {}),
          (('div',), {'id': 'fb-root'}),
          (('div',), {'class': 'et_pb_section'}),
          (('div',), {'class': 'en-page-navi'}),
          (('div',), {'class': 'et_pb_article_offerer_article'}),
          (('div',), {'class': 'en_gallery_holder'}),
          (('div',), {'class': 'enews-article-offerer-info'})]

MEDIA_LIST = [(('div',), {'class': 'fb-video'}),
              (('div',), {'class': 'en_gallery_slider'}),
              (('div',), {'class': 'fb-post'}),
              (('div',), {'class': 'wp-video'}),
              (('blockquote',), {'class': 'twitter-tweet'}),
              (('div',), {'class': 'wp-caption'})]


def decompose_spec(article_dec):
    decompose_listed_subtrees_and_mark_media_descendants(article_dec, DECOMP, MEDIA_LIST)
    return article_dec


BLACKLIST_SPEC = ['https://www.magyaridok.hu/elofizetoi-aszf/',
                  'https://www.magyaridok.hu/adatvedelem/',
                  'https://www.magyaridok.hu/impresszum/',
                  'https://www.magyaridok.hu/gdpr/',
                  'https://www.magyaridok.hu/mediaajanlat/',
                  'https://www.magyaridok.hu/belfold/teszt-cikk-1105-bm-99016/',
                  'https://www.magyaridok.hu/gazdasag/lorem-ipsum-facts-692203/',
                  'https://www.magyaridok.hu/eletmod/percrol-percre-teszt-2-886234/']
LINK_FILTER_SUBSTRINGS_SPEC = re.compile('|'.join(['LINK_FILTER_DUMMY_STRING']))

MULTIPAGE_URL_END = re.compile(r'^\b$')  # Dummy


def next_page_of_article_spec(_):
    return None
