#!/usr/bin/env python3
# -*- coding: utf-8, vim: expandtab:ts=4 -*

import re

from html2tei import parse_date, BASIC_LINK_ATTRS, decompose_listed_subtrees_and_mark_media_descendants, \
    tei_defaultdict

PORTAL_URL_PREFIX = 'https://www.blikk.hu'

ARTICLE_ROOT_PARAMS_SPEC = [
    (('section',), {'class': 'leftSide'})]  # <section class="col-12 col-lg-8 mx-auto mx-lg-0 leftSide">


SUBJECT_DICT = {'eletmod': 'életmód',
                'galeria': 'galéria',
                'allati': 'állati',
                'egeszseg': 'egészség',
                'sztarvilag': 'sztárvilág',
                'utazas': 'utazás',
                'aktualis': 'aktuális',
                'hoppa': 'hoppá',
                'karacsony': 'karácsony',
                'husvet': 'húsvét',
                'lelek': 'lélek',
                'tavaszi-megujulas': 'tavaszi-megújulás',
                'adventi-teendok': 'adventi-teendők',
                'dizajn': 'dizájn',
                'unnepi-tippek': 'ünnepi-tippek'}


def get_meta_from_articles_spec(tei_logger, url, bs):
    """author tag does not exist"""
    data = tei_defaultdict()
    data['sch:url'] = url

    article_root = bs.find('section', {'class': 'leftSide'})
    if article_root is not None:

        # NAME
        title_tag = article_root.find('section', {'class': 'mainTitle'})
        if title_tag is not None:
            title_text_tag = title_tag.find('h1')
            if title_text_tag is not None:
                title_text = title_text_tag.get_text(strip=True)
                if len(title_text) > 0:
                    data['sch:name'] = title_text
                else:
                    tei_logger.log('WARNING', f'{url}: TITLE TEXT EMPTY!')
            else:
                tei_logger.log('WARNING', f'{url}: TITLE TEXT TAG NOT FOUND!')
        else:
            tei_logger.log('WARNING', f'{url}: TITLE SECTION TAG NOT FOUND!')

        # DATE PUBLISHED
        date_published = article_root.find('div', {'class': 'dates d-flex flex-column flex-md-row'}).get_text(strip=True)
        if date_published is not None:
            data['sch:datePublished'] = parse_date(date_published, "%Y. %b %d. %H:%M")  # TODO error handling?
        else:
            tei_logger.log('WARNING', f'{url}: DATE PUBLISHED TAG NOT FOUND!')

        # DATE MODIFIED

        # AUTHORS
        authors_section = article_root.find('div', {'id': 'authors'})
        if authors_section is not None:
            authors = authors_section.find_all('p', {'class': 'authorName'})
            if len(authors) > 0:  # TODO it has Blikk-információ
                data['sch:author'] = [t.get_text(strip=True) for t in authors if len(t.get_text(strip=True)) > 0]
            else:
                tei_logger.log('DEBUG', f'{url}: NO AUTHORS FOUND!')
        else:
            tei_logger.log('DEBUG', f'{url}: NO AUTHOR SECTION FOUND!')

        # ARTICLE SECTION
        # TODO article section in url or meta?

        # KEYWORDS
        keywords_section = article_root.find('section', {'class': 'row w-100 mt-2 mb-3 bottomTags'})
        if keywords_section is not None:
            kw_tags = keywords_section.find_all('a')
            if len(kw_tags) > 0:
                data['sch:keywords'] = [t.get_text(strip=True) for t in kw_tags if len(t.get_text(strip=True)) > 0]
            else:
                tei_logger.log('DEBUG', f'{url}: NO KEYWORD TAGS FOUND!')
        else:
            tei_logger.log('DEBUG', f'{url}: NO KEYWORDS SECTION FOUND!')

    return data


def excluded_tags_spec(tag):
    return tag


BLOCK_RULES_SPEC = {}
BIGRAM_RULES_SPEC = {}

LINKS_SPEC = BASIC_LINK_ATTRS
DECOMP = [(('style',), {}),
          (('script',), {}),
          (('footer',), {}),
          (('section',), {'class': 'breadcrumbs'}),
          (('section',), {'class': 'mainTitle'}),
          (('section',), {'class': 'datesAndShareContainer'}),
          (('div',), {'id': 'authors'}),
          (('div',), {'id': 'bannerDesktopContainer stickyContainer'}),
          (('div',), {'id': 'articleOfferFlag'}),
          (('div',), {'id': 'underArticleAdvertisement'}),
          (('section',), {'class': 'bottomTags'}),
          (('section',), {'class': 'socialShare'}),
          (('div',), {'class': 'rltdwidget'}),
          (('h4',), {'class': 'mb-3'}),
          (('div',), {'id': 'fb-root'}),
          (('section',), {'id': 'comments'})
          ]


MEDIA_LIST = []


def decompose_spec(article_dec):
    decompose_listed_subtrees_and_mark_media_descendants(article_dec, DECOMP, MEDIA_LIST)
    return article_dec


BLACKLIST_SPEC = ['https://www.blikk.hu/prospektus/penny-market/penny-market-marciusi-akcios-ujsag/kyvtf51',
                  'https://www.blikk.hu/prospektus/aldi/aldi-aprilisi-akcios-ujsag/2c457l2']

LINK_FILTER_SUBSTRINGS_SPEC = re.compile('|'.join(['LINK_FILTER_DUMMY_STRING']))

MULTIPAGE_URL_END = re.compile(r'^\b$')  # Dummy


def next_page_of_article_spec(_):
    return None
