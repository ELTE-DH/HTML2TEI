#!/usr/bin/env python3
# -*- coding: utf-8, vim: expandtab:ts=4 -*

import re

from src.html2tei import parse_date, BASIC_LINK_ATTRS, decompose_listed_subtrees_and_mark_media_descendants, \
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
