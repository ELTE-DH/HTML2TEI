#!/usr/bin/env python3
# -*- coding: utf-8, vim: expandtab:ts=4 -*

import re
from os.path import join as os_path_join, dirname as os_path_dirname, abspath as os_path_abspath

from html2tei import parse_date, BASIC_LINK_ATTRS, decompose_listed_subtrees_and_mark_media_descendants, tei_defaultdict

PORTAL_URL_PREFIX = 'https://hirado.hu'

ARTICLE_ROOT_PARAMS_SPEC = [(('div',), {'class': 'articleContent'})]

HTML_BASICS = {'p', 'h3', 'h2', 'h4', 'h5', 'em', 'i', 'b', 'strong', 'mark', 'u', 'sub', 'sup', 'del', 'strike',
               'ul', 'ol', 'li', 'table', 'tr', 'td', 'th', 'quote', 'figure', 'iframe', 'script', 'noscript'}

SOURCE_LIST = ['ap', 'bartók rádió', 'blikk', 'borsonline', 'brilliance kft', 'dankó rádió', 'dining guide',
               'duna televízió', 'duna tv', 'duna word', 'duna world', 'duna', 'dunatv', 'facebook', 'fordítás',
               'furbify laptop', 'hirado.', 'hirado.hu', 'honvedelem.hu', 'hungaroring.hu', 'híradó.hu', 'inforádió',
               'koronavirus.gov.hu', 'kossuth rádió', 'közért+', 'liget budapest projekt', 'm1 híradó', 'm1', 'm1. mti',
               'm2 petőfi', 'm2', 'm5', 'magyar\xa0franchise\xa0szövetség', 'magyar nemzet', 'mandiner', 'mandiner.hu',
               'met.hu', 'mn', 'mnb', 'mnb.hu', 'mti archív', 'mti', 'mtva', 'múlt-kor', 'nemzeti sport',
               'nyomkovetes.net', 'omsz fb', 'origo', 'ots', 'pallas athéné könyvkiadó (pabooks)', 'petõfi rádió',
               'police.hu', 'rubicon', 'századvég gazdaságkutató zrt.', 'századvég', 'treningakademia.hu', 'uip',
               'ujvarosonline.hu', 'v4na', 'vg.hu', 'várkapitányság', 'wikipedia', 'wikipedia.org', 'wikipédia',
               'zoobudapest.com', 'átadták a felújított arany-palotát nagyszalontán']


def encoding_correction(input_str, mode):
    """
    corrects encoding errors on the site
    params:
        - input_str: input str
        - mode: bool, whether there is an encoding error
    """
    if mode is False:
        return input_str
    elif mode is True:
        try:
            return input_str.encode('raw_unicode_escape').decode('UTF-8')
        except UnicodeDecodeError:
            return input_str[:-1].encode('raw_unicode_escape').decode('UTF-8')
    else:
        raise ValueError('mode argument must be boolean')


def get_meta_from_articles_spec(tei_logger, url, bs):
    data = tei_defaultdict()
    data['sch:url'] = url

    title = bs.find('meta', {'property': 'og:title', 'content': True})
    # check whether the encoding is correct
    encodingerror = True
    if title is not None:
        title = title.attrs['content'].strip()
        try:
            title = encoding_correction(title, encodingerror)
        except UnicodeDecodeError:
            encodingerror = False
        data['sch:name'] = title
    else:
        tei_logger.log('WARNING', f'{url}: TITLE TAG NOT FOUND!')

    article_root = bs.find('div', class_='bodywrapper')
    if article_root is not None:
        date_tag = article_root.find('div', class_='artTime')
        if date_tag is not None:
            date_text = date_tag.text.strip()
            if date_text is not None:
                data['sch:datePublished'] = parse_date(date_text, '%Y. %m. %d. - %H:%M')
            else:
                tei_logger.log('WARNING', f'{url}: DATE FORMAT ERROR!')
        else:
            tei_logger.log('WARNING', f'{url}: DATE TAG NOT FOUND!')

        source_author_list = []
        author = article_root.find('div', class_='artAuthor')
        source = article_root.find('div', class_='artSource')
        if author is not None:
            author.span.decompose()
            source_author_list += [encoding_correction(t.strip(), encodingerror) for t in re.split('[/,]', author.text)]
        if source is not None:
            source.span.decompose()
            source_author_list += [encoding_correction(t.strip(), encodingerror) for t in re.split('[/,]', source.text)]
        if len(source_author_list) > 0:
            author_list = []
            source_list = []
            [source_list.append(e) if e.lower() in SOURCE_LIST else author_list.append(e) for e in source_author_list]
            if len(author_list) > 0:
                data['sch:author'] = author_list
            if len(source_list) > 0:
                data['sch:source'] = source_list
        else:
            tei_logger.log('WARNING', f'{url}: NEITHER SOURCE NOR AUTHOR TAG WAS FOUND!')

        section_tag = article_root.find('div', class_='breadCrumbs')
        if section_tag is not None:
            section_tree = section_tag.text.split('/')
            data['sch:articleSection'] = encoding_correction(section_tree[1].strip(), encodingerror)
            if len(section_tree) > 2:
                data['subsection'] = encoding_correction(section_tree[-1].strip(), encodingerror)
        else:
            tei_logger.log('WARNING', f'{url}: SECTION TAG NOT FOUND!')
    else:
        tei_logger.log('WARNING', f'{url}: ARTICLE BODY NOT FOUND OR UNKNOWN ARTICLE SCHEME!')

    return data


def excluded_tags_spec(tag):
    if tag.name not in HTML_BASICS:
        tag.name = 'else'
    tag.attrs = {}
    return tag


BLOCK_RULES_SPEC = {}
BIGRAM_RULES_SPEC = {}
LINKS_SPEC = BASIC_LINK_ATTRS
DECOMP = [(('div',), {'class': 'articleSocial'}),
          (('div',), {'class': 'interestingRecommended'}),
          (('div',), {'class': 'hms-banner-wrapper roadblock'}),
          (('script',), {})]

LINK_FILTER_SUBSTRINGS_SPEC = re.compile('|'.join(['LINK_FILTER_DUMMY_STRING']))
MEDIA_LIST = [(('div',), {'class': 'video'}),
              (('div',), {'class': 'galleryContener'}),
              (('div',), {'class': 'galleryHeadContener'}),
              (('div',), {'class': 'hms_fb_post_embed'}),
              (('div',), {'class': 'articlePic aligncenter'}),
              (('div',), {'class': 'live-player-container'}),
              (('div',), {'class': 'twitter-tweet twitter-tweet-rendered'}),
              (('div',), {'role': 'img'}),
              (('div',), {'class': 'embed-container'}),
              (('div',), {'class': 'articlePic articleGallery'}),
              (('div',), {'style': 'display: none;'}),
              (('img',), {}),
              (('iframe',), {})]


def decompose_spec(article_dec):
    decompose_listed_subtrees_and_mark_media_descendants(article_dec, DECOMP, MEDIA_LIST)
    return article_dec


BLACKLIST_SPEC = [url.strip() for url in open(os_path_join(os_path_dirname(os_path_abspath(__file__)),
                                                           'hiradohu_BLACKLIST.txt')).readlines()]

MULTIPAGE_URL_END = re.compile(r'^\b$')  # Dummy


def next_page_of_article_spec(_):
    return None
