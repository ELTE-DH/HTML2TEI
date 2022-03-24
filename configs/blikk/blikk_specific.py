#!/usr/bin/env python3
# -*- coding: utf-8, vim: expandtab:ts=4 -*

import re
from os.path import join as os_path_join, dirname as os_path_dirname, abspath as os_path_abspath

from html2tei import parse_date, BASIC_LINK_ATTRS, decompose_listed_subtrees_and_mark_media_descendants, \
    tei_defaultdict

PORTAL_URL_PREFIX = 'https://www.blikk.hu'

ARTICLE_ROOT_PARAMS_SPEC = [
    (('section',), {'class': 'leftSide'})]  # <section class="col-12 col-lg-8 mx-auto mx-lg-0 leftSide">


TOPIC_AND_ADVERT_SUBTITLES = ['Hirdetés',
                              'A Tvr-hét ajánlja!',
                              'A Tv-hét ajánlja!',
                              'Szponzorált tartalom',
                              'Szponzorált tartalom!',
                              'Szonzorált tartalom',
                              'Támogatott tartalom',
                              'Koronavírus']

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
                'unnepi-tippek': 'ünnepi-tippek',
                'baleset-info': 'baleset-info',
                'belfold': 'belföld',
                'kulfold': 'külföld',
                'divat': 'divat',
                'velemeny': 'vélemény',
                'erotika': 'erotika',
                'kultura': 'kultúra',
                'streaming': 'streaming',
                'zene': 'zene',
                'auto': 'autó',
                'hetvegere': 'hétvégére',
                'rio-2016': 'Rio 2016',
                'sztarsztorik': 'sztársztorik',
                'blikk-tv': 'blikk-tv',
                'garazs': 'garázs',
                'geo': 'geo',
                'gasztro': 'gasztro',
                'penz': 'pénz',
                'magyar-foci': 'magyar-foci',
                'hoppa': 'hoppá',
                'panorama': 'panoráma',
                'wtf': 'wtf',
                'filmklikk': 'filmklikk',
                'mindent-bele': 'mindent-bele',
                'gyors-ebed': 'gyors-ebéd',
                'tech': 'tech',
                'forma-1': 'forma-1',
                'durva': 'durva',
                'egyeni': 'egyéni',
                'a-nyulon-tul': 'a-nyúlon-túl',
                'retro-receptek': 'retró-receptek',
                'vilag-titkai': 'világ-titkai',
                'napi-ajanlat': 'napi-ajánlat',
                'speedzone': 'speedzone',
                'teszt': 'teszt',
                'szexi': 'szexi',
                'olimpia2021': 'olimpia2021',
                'erdekes': 'érdekes',
                'veszhelyzet': 'vészhelyzet',
                'sport': 'sport',
                'foci-eb-2016': 'foci-eb-2016',
                'husveti-tippek': 'húsvéti-tippek',
                'egyeb': 'egyéb',
                'kulfoldi-foci': 'külfoldi-foci',
                'politika': 'politika',
                'tippek': 'tippek',
                'edessegek': 'édességek',
                'konnyu-vacsora': 'könnyű-vacsora',
                'menetproba': 'menetpróba',
                'tavaszi-megujulas': 'tavaszi-megújulás',
                'egeszsegkalauz': 'egészségkalaúz',
                'eb-2021': 'eb-2021',
                'katalogus': 'katalógus',
                'receptek': 'receptek',
                'valasztas-2022': 'választás-2022',
                'spanyol-foci': 'spanyol-foci',
                'krimi': 'krimi',
                'csapat': 'csapat',
                'lol': 'lol',
                'vizes-vb': 'vizes-vb',
                'foci-vb-2018': 'foci-vb-2018',
                'magyar-japan-noi-vizilabda': 'magyar-japan-noi-vizilabda'
                }



def get_meta_from_articles_spec(tei_logger, url, bs):
    """author tag does not exist"""
    data = tei_defaultdict()
    data['sch:url'] = url

    article_root = bs.find('section', {'class': 'leftSide'})
    if article_root is not None:

        # NAME - TITLE
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
        date_published_tag = article_root.find('div', {'class': 'dates d-flex flex-column flex-md-row'})
        if date_published_tag is not None:
            date_published = date_published_tag.get_text(strip=True)
            if len(date_published) > 0:
                data['sch:datePublished'] = parse_date(date_published, "%Y. %b %d. %H:%M")  # TODO error handling?
            else:
                tei_logger.log('WARNING', f'{url}: DATE PUBLISHED TAG TEXT EMPTY!')
        else:
            tei_logger.log('WARNING', f'{url}: DATE PUBLISHED TAG NOT FOUND!')

        # DATE MODIFIED - no date modified information found

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
        article_section_meta_tag = bs.find('meta', {'property':'article:section', 'content':True})
        if article_section_meta_tag is not None:
            section_text = article_section_meta_tag['content'].strip()
            if len(section_text) > 1:  # content text may be '/'
                data['sch:articleSection'] = section_text
        
        # KEYWORDS
        keywords = []

        keywords_section = article_root.find('section', {'class': 'row w-100 mt-2 mb-3 bottomTags'})
        if keywords_section is not None:
            kw_tags = keywords_section.find_all('a')
            if len(kw_tags) > 0:
                for t in kw_tags:
                    if len(t.get_text(strip=True)) > 0:
                        keywords.append(t.get_text(strip=True)) 
            else:
                tei_logger.log('DEBUG', f'{url}: NO KEYWORD TAGS FOUND!')
        else:
            tei_logger.log('DEBUG', f'{url}: NO KEYWORDS SECTION FOUND!')

        # additional text is taken from section-path tag which contains path elements from the url 
        # these elements are considered keywords
        section_path_tag = bs.find('meta', {'name': 'kt:section-path', 'content':True})
        if section_path_tag is not None:
            section_path_text_split = section_path_tag['content'].strip().split('/')
            section_path_elements = [t for t in section_path_text_split if len(t) > 1]

            # possible keywords are manually collated in the SUBJECT DICT dictionary. 
            for extra_keyword in section_path_elements:
                if extra_keyword in SUBJECT_DICT.keys() and extra_keyword != data['sch:artcleSection']:
                    keywords.append(SUBJECT_DICT[extra_keyword])
                else:
                    tei_logger.log('DEBUG', f'{url}: SECTION PATH KEYWORD NOT IN SPECIFIC FILE SUBJECT DICT!')

        # additional text is taken from the subtitle tag which is sometimes used to annotate sponsored articles
        # these elements are considered keywords
        subtitle_tag = article_root.find('div', {'class': 'subtitle'})
        if subtitle_tag is not None:
            stripped_subtitle_tag = subtitle_tag.get_text(strip=True)
            if stripped_subtitle_tag in TOPIC_AND_ADVERT_SUBTITLES:
                keywords.append(stripped_subtitle_tag)
            elif len(stripped_subtitle_tag) > 0:
                data['sch:alternateName'] = stripped_subtitle_tag

        if len(keywords) > 0:
            data['sch:keywords'] = keywords

    return data


def excluded_tags_spec(tag):
    tag_attrs = tag.attrs
    if tag.name == 'div' and 'data-embed-id' in tag_attrs.keys():
        tag_attrs['data-embed-id'] = '@DATA-EMBED-ID'
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
          (('section',), {'id': 'comments'}),
          (('div',), {'class':'detailRightSide'})  # featured articles on right side
          ]


MEDIA_LIST = []


def decompose_spec(article_dec):
    decompose_listed_subtrees_and_mark_media_descendants(article_dec, DECOMP, MEDIA_LIST)
    # the following subtitle tag contents are added to keywords to allow future
    # filtering for sponsored content 
    for f in reversed(article_dec.find_all('div', {'class':'subtitle'})):
        if ('Hirdetés' or 'A Tvr-hét ajánlja!' or 'Szponzorált tartalom') in f.text:
            f.decompose()

    # <p> tag at the end of an article used for recommending further articles is decomposed
    detail_section = article_dec.find('section', class_='detail')
    if detail_section is not None:
        all_immediate_detail_tags = detail_section.find_all(recursive=False)
        if len(all_immediate_detail_tags) > 1:
            check = lambda t: t.name == 'div' and 'class' in t.attrs.keys() and t['class'] == ['live_article_section']
            for f in all_immediate_detail_tags:
                if f.name == 'p' and check(all_immediate_detail_tags[-2]) is True:
                    link_tag = f.find('a', {'id':True, 'rel':True, 'href':True})
                    if link_tag is not None and 'blikk.hu' in link_tag['href']:
                        f.decompose()

    return article_dec


BLACKLIST_SPEC = [url.strip() for url in open(os_path_join(os_path_dirname(os_path_abspath(__file__)),
                                                           'blikk_empty_BLACKLIST.txt')).readlines()] + \
                 ['https://www.blikk.hu/prospektus/penny-market/penny-market-marciusi-akcios-ujsag/kyvtf51',
                  'https://www.blikk.hu/prospektus/aldi/aldi-aprilisi-akcios-ujsag/2c457l2',
                  'https://www.blikk.hu/teszt/kxd74tx']

bad_url_list = ['http://read://https_www.foxnews.com/?url=https%3A%2F%2Fwww.foxnews.com%2Fentertainment%2Fcharlize-theron-dating-herself-her-daughter-said-she-needs-boyfriend',
                'http://read://https_www.foxnews.com/?url=https://www.foxnews.com/entertainment/charlize-theron-dating-herself-her-daughter-said-she-needs-boyfriend',
                '//gdehu.hit.gemius.pl/_%%CACHEBUSTER%%/redot.gif?id=0nHlDa9qUQ.ZK6S5vQMx2pPanOju_9hLgs1k4l88n_H.p7/fastid=faqnnauibqujdjjoncywdnnoisla/stparam=onhehpijse/nc=0']

LINK_FILTER_SUBSTRINGS_SPEC = re.compile('|'.join([re.escape(s) for s in bad_url_list]))

MULTIPAGE_URL_END = re.compile(r'^\b$')  # Dummy


def next_page_of_article_spec(_):
    return None
