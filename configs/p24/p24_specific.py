#!/usr/bin/env python3
# -*- coding: utf-8, vim: expandtab:ts=4 -*

import re

from html2tei import parse_date, BASIC_LINK_ATTRS, decompose_listed_subtrees_and_mark_media_descendants, tei_defaultdict

PORTAL_URL_PREFIX = 'https://24.hu'

HTML_BASICS = {'p', 'h3', 'h2', 'h4', 'h5', 'em', 'i', 'b', 'strong', 'mark', 'u', 'sub', 'sup', 'del', 'strike',
               'ul', 'ol', 'li', 'table', 'tr', 'td', 'th', 'quote', 'figure', 'iframe', 'script', 'noscript'}

ARTICLE_ROOT_PARAMS_SPEC = [(('div',), {'class': ['o-post__cntWrap']}),
                            (('div',), {'class': ['m-wideContent__cnt']})
                            ]

SUBJECT_DICT = {'kulfold': 'külföld',
                'belfold': 'belföld',
                'gazdasag': 'gazdaság',  # fn
                'kultura': 'kultúra',
                'tech': 'tech',
                'elet-stilus': 'élet-stílus',
                'szorakozas': 'szórakozás',
                '24-podcast': 'podcast',
                'kozelet': 'közélet',
                'europoli': 'europoli',
                'uzleti-tippek': 'üzleti tippek',  # fn
                'tudomany': 'tudomány',
                'sport': 'sport',
                'otthon': 'otthon',
                'velemeny': 'vélemény',
                'video': 'videó'
                }


def get_meta_from_articles_spec(tei_logger, url, bs):
    data = tei_defaultdict()
    data['sch:url'] = url

    data['sch:url'] = url

    body_newsfeed = bs.find('section', {'id': ['hirfolyam']})

    # AUTHOR(s)
    author_list = []

    # Displayed author at the top of all articles (includes: 'admin', '24.hu')
    authors = bs.find_all('a', {'class': 'm-author__name'})
    if len(authors) > 0:
        for author_tag in authors:
            author_name = author_tag.get_text(strip=True)
            if author_name is not None:
                author_list.append(author_name)
            else:
                tei_logger.log('DEBUG', f'{url}: EMPTY AUTHOR TAG FOUND!')
    else:
        tei_logger.log('WARNING', f'{url}: NO AUTHOR TAG FOUND!')

    # This scenario is for newsfeed formats, where multiple authors contribute to a stream of articles
    if body_newsfeed is not None:

        authors = body_newsfeed.find_all('div', {'class': ['livepost-event-author']})
        print(len(authors))
        if len(authors) > 1:
            for author_tag in authors:
                author_name = author_tag.get_text(strip=True)
                if author_name is not None:
                    author_list.append(author_name)
                # first section adds 'main' author, which in newsfeed formats is usually '24.hu', so is removed here
                if len(author_list) > 1 and '24.hu' in author_list:
                    author_list.remove('24.hu')
        else:
            tei_logger.log('WARNING', f'{url}: COULD NOT FIND NEWSFEED ARTICLE AUTHORS!')

    if len(author_list) > 0:  # Previous two clauses should throw errors when authors not found
        data['sch:author'] = list(set(author_list))  # TODO might be okay to pass just set?

    date = bs.find('span', {'class': ['o-post__date', 'a-date', 'fl']})
    if date is not None:
        # Where modification date is not indicated (most cases) the span tag only has its contents as a single child
        if len(list(date.children)) == 1:
            date_text = date.get_text(strip=True)
            if date_text is not None:
                data['sch:DatePublished'] = parse_date(date_text, '%Y. %m. %d. %H:%M')

        # In newsfeed formats and select articles, the date tag includes other tags such as date modified
        elif len(list(date.children)) > 1:
            date_created = date.find('span', {'class': "m-author__catDateTitulusCreateDate"}).get_text(strip=True)
            if date_created is not None:
                data['sch:DatePublished'] = parse_date(date_created, '%Y. %m. %d. %H:%M')

        else:
            tei_logger.log('WARNING', f'{url}: DATE PUBLISHED TAG NOT FOUND!')

    else:
        tei_logger.log('WARNING', f'{url}: COULD NOT FIND DATE PUBLISHED TAG!')

    # DATE MODIFIED - only displayed in a few cases, therefore taken from <meta> tag
    # e.g.: https://24.hu/belfold/2018/04/08/itt-a-nagy-nap-valasztas-2018-elozzuk/8/
    date_modified_tag = bs.find('meta', {'property': 'article:modified_time'})
    if date_modified_tag is not None and 'content' in date_modified_tag.attrs:
        date_modified = date_modified_tag['content']
        if date_modified is not None:
            p_date = parse_date(date_modified.strip(), '%Y-%m-%dT%H:%M:%SZ')
            data['sch:DateModified'] = p_date
        else:
            tei_logger.log('WARNING', f'{url}: DATE MODIFIED TAG NOT FOUND!')

    # ARTICLE SECTION (from url)
    # TODO is this error handling okay?
    section_match = None

    try:
        # match all lowercase characters between https://24.hu and /
        section_match = re.search(r'(?<=https://24\.hu/)[a-z]+(?=/)', url).group()
    except AttributeError as err:
        tei_logger.log('WARNING', f'{url}: {type(err)} COULD NOT MATCH ARTICLE SECTION IN URL')

    if section_match == 'fn':  # Finance sections start with 24.hu/fn/...
        try:
            # match all lowercase characters between https://24.hu/fn/ and /
            section_match = re.search(r'(?<=https://24\.hu/fn/)[a-z]+(?=/)', url).group()
        except AttributeError as err:
            tei_logger.log('WARNING', f'{url}: {type(err)} COULD NOT MATCH ARTICLE SECTION IN URL')

    if section_match in SUBJECT_DICT.keys():
        data['sch:articleSection'] = SUBJECT_DICT[section_match]
    else:
        tei_logger.log('WARNING', f'{url}: ARTICLE SECTION TAG NOT FOUND!')

    # NAME AND KEYWORDS
    main_column = bs.find('div', {'class': ['o-post', 'o-cnt', 'm-post24']})
    if main_column is not None:

        # NAME
        title_tag = main_column.find('h1', {'class': 'o-post__title'})
        if title_tag is not None:
            title_text = title_tag.find('span').get_text(strip=True)
            if title_text is not None:
                data['sch:name'] = title_text
            else:
                tei_logger.log('WARNING', f'{url}: ARTICLE NAME TAG NOT FOUND!')

        # KEYWORDS
        keyword_tags = main_column.find_all('a', {'class': 'm-tag__links'})
        keywords = []
        if len(keyword_tags) > 0:
            for keyword_tag in keyword_tags:
                keyword_text = keyword_tag.get_text(strip=True)
                if keyword_text is not None:
                    keywords.append(keyword_text)
                else:
                    tei_logger.log('WARNING', f'{url}: EMPTY KEYWORD TAG!')
            if len(keywords) > 0:
                data['sch:keywords'] = keywords
            else:
                tei_logger.log('DEBUG', f'{url}: KEYWORDS NOT FOUND!')
        else:
            tei_logger.log('DEBUG', f'{url}: KEYWORD TAGS NOT FOUND!')

    return data


def excluded_tags_spec(tag):  # TODO commented out for running html2tei functions
    # if tag.name not in HTML_BASICS:
    #     tag.name = 'else'
    # tag.attrs = {}

    return tag


BLOCK_RULES_SPEC = {}
BIGRAM_RULES_SPEC = {}
LINKS_SPEC = {}

# TODO The only container which has the whole article in it also contains a bunch of ads and recommendations
DECOMP = [(('div',), {'class': 'o-post__authorShare m-social cf _ce_measure_widget'}),
          (('div',), {'class': 'a-hirstartRecommender _ce_measure_widget'}),
          (('div',), {'class': 'widget m-recommendedVideoWidget cf _ce_measure_widget'}),
          (('div',), {'class': 'widget m-articleWidget m-articleListWidget _ce_measure_widget h24-col-2 real-size-8'}),
          (('div',), {'class': 'widget m-articleWidget m-articleListWidget _ce_measure_widget h24-col-2 real-size-8'}),
          (('div',), {'class': 'banner-container clearfix clear-banner-row'}),
          (('div',), {'class': 'banner-container clearfix'}),
          (('div',), {'class': 'm-fbComment__txtAndIframeWrap'}),
          (('div',), {'class': 'm-authorRecommend cf _ce_measure_widget'}),
          (('div',), {'class': 'm-authorRecommend cf _ce_measure_widget'}),
          (('div',), {'class': 'o-articleHead m-post24'})  # TODO this is for the title and title picture.
          ]

MEDIA_LIST = []


def decompose_spec(article_dec):
    decompose_listed_subtrees_and_mark_media_descendants(article_dec, DECOMP, MEDIA_LIST)
    return article_dec


BLACKLIST_SPEC = []
LINK_FILTER_SUBSTRINGS_SPEC = re.compile('|'.join(['LINK_FILTER_DUMMY_STRING']))

MULTIPAGE_URL_END = re.compile(r'^\b$')  # Dummy


def next_page_of_article_spec(_):
    return None
