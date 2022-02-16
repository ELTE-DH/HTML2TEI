#!/usr/bin/env python3
# -*- coding: utf-8, vim: expandtab:ts=4 -*-

import re

from bs4 import BeautifulSoup

from html2tei import parse_date, decompose_listed_subtrees_and_mark_media_descendants, tei_defaultdict

PORTAL_URL_PREFIX = 'https://444.hu/'
ARTICLE_ROOT_PARAMS_SPEC = [(('main',), {'id': 'content-main'})]  # ,(('section',), {'id': 'main-section'})]

HIGHLIGHT = re.compile(r'.*highlight.*')
A_TAGS = {'a', '0_MDESC_a'}

# https://444.hu/2015/03/15/24-ora-az-uj-kozmediaval?page=4  más szerkezetű cikk
# https://444.hu/2016/06/15/oroszorszag-szlovakia-elo?page=3 közvetítés author, section
# https://444.hu/2016/02/10/ejjel-erkezem-mondta-a-ciklon  üresnek írja de nem az jelenleg
# https://444.hu/2014/05/10/orban-viktor-eskuszik-elo?page=2
# https://444.hu/2021/02/18/mar-megint-24-ora-a-kozmediaval?page=6


def get_meta_from_articles_spec(tei_logger, url, bs):
    data = tei_defaultdict()
    data['sch:url'] = url
    basic_article = True
    raw_meta = bs.find('div', {'id': 'headline'})
    articles = bs.find_all('article')  # TODO
    report = bs.find_all('article', {'class': 'report', 'data-content-id': True})
    if raw_meta is not None:
        """if len(articles) > 1 and all('class' in art.attrs.keys() and art.attrs['class'] == ['report']
                                     for art in articles):
            basic_article = False"""
        if len(report) > 1:
            print('report', url)
            basic_article = False
    else:
        tei_logger.log('WARNING', f'{url}: ARTICLE BODY NOT FOUND OR UNKNOWN ARTICLE SCHEME!')
        return None

    if basic_article in [True, False]:
        date_tag = bs.find('meta', property='article:published_time')
        # 2021-05-11T19:31:11+02:00"
        if date_tag is not None:
            parsed_date = parse_date(date_tag.attrs['content'][:19], '%Y-%m-%dT%H:%M:%S')
            data['sch:datePublished'] = parsed_date
        else:
            tei_logger.log('WARNING', f'{url}: DATE NOT FOUND IN URL!')
        modified_date = bs.find('meta', property='article:modified_time').attrs['content']
        if modified_date is not None:
            parsed_moddate = parse_date(modified_date[:19], '%Y-%m-%dT%H:%M:%S')
            data['sch:dateModified'] = parsed_moddate
        lead_tag = bs.find('meta', {'name': 'description'})
        if lead_tag is not None:
            lead_text = lead_tag.attrs['content'].strip()
            data['sch:abstract'] = lead_text

    if basic_article is True:
        title = raw_meta.find('h1')
        if title is not None:
            data['sch:name'] = title.text.strip()
        else:
            tei_logger.log('WARNING', f'{url}: TITLE TAG NOT FOUND!')
        authors_list = raw_meta.find(class_='byline__authors')
        if authors_list is not None:
            authors_list = [a.text.strip() for a in authors_list.find_all('a')]
            data['sch:author'] = authors_list
        else:
            tei_logger.log('WARNING', f'{url}: AUTHOR TAG NOT FOUND!')
        section = raw_meta.find(class_='byline__category')
        if section is not None:
            data['sch:articleSection'] = section.text.strip()
        else:
            tei_logger.log('DEBUG', f'{url}: SECTION TAG NOT FOUND!')
        keywords_root = bs.find('meta', {'name': 'keywords'})
        if keywords_root is not None:
            keywords_list = keywords_root.attrs['content'].split(',')
            data['sch:keywords'] = keywords_list
        lead_tag = bs.find('meta', {'name': 'description'})
        if lead_tag is not None:
            lead_text = lead_tag.attrs['content'].strip()
            data['sch:abstract'] = lead_text
        return data
    elif not basic_article:
        # The scheme of broadcasts is different, metadata is handled differently
        authors_tag = bs.find_all(class_='report__author')
        if authors_tag is not None:
            authors_list = [au.text.strip() for au in authors_tag]
            data['sch:author'] = authors_list
        section = bs.find('meta', {'itemprop': 'articleSection'})
        if section is not None and 'content' in section.attrs.keys():
            data['sch:articleSection'] = section.attrs['content'].strip()
        title = bs.find('h1', {'class': 'livestream__title'})
        if title is not None:
            data['sch:name'] = title.text.strip()
    return data

# https://444.hu/2016/02/10/ejjel-erkezem-mondta-a-ciklon scripttel töltődik ki a cikktörzs szövege


def excluded_tags_spec(tag):
    tag_attrs = tag.attrs
    if 'class' in tag_attrs.keys() and HIGHLIGHT.match(str(tag_attrs['class'])):
        tag_attrs['class'] = '@HL'
    if tag.name in A_TAGS and 'title' in tag_attrs.keys():
        tag_attrs['title'] = '@title'
    elif tag.name == 'table' and 'class' in tag_attrs.keys():
        tag_attrs['class'] = '@class'
    return tag


BLOCK_RULES_SPEC = {}
BIGRAM_RULES_SPEC = {'szakasz': {('temp_table_id', 'det_by_child'): ('table_text', 'temp')}}
# kozvetites meta: span > kozvetites_ido

LINKS_SPEC = {'a': 'href', '0_MDESC_a': 'href', 'img': 'href', '0_MDESC_img': 'href'}
DECOMP = [(('div',), {'id': 'headline'}),
          (('div',), {'class': 'hide-print'}),
          (('div',), {'class': 'hide-for-print'}),  # class=row hide-for-print
          (('aside',), {'id': 'content-sidebar'}),
          (('div',), {'id': 'ep-banner'}),
          (('div',), {'class': 'widget-recommendation'}),
          (('script',), {}),
          (('noscript',), {}),
          (('iframe',), {}),
          (('center',), {}),
          (('style',), {}),  # css
          (('footer',), {}),
          (('footer',), {'class': 'hide-print'}),
          (('footer',), {'class': 'hide-for-print'}),
          (('div',), {'class': 'jeti-roadblock'}),
          (('div',), {'class': 'tumblr-post'}),
          (('div',), {'class': 'd36-top'}),
          (('div',), {'id': 'epaperPromoBox'}),
          (('div',), {'id': 'actions'}),
          (('div',), {'id': 'content'}),
          (('span',), {'class': 'embed-444'}),  # hirdetés
          (('div',), {'class': 'fb-root'}),
          (('div',), {'id': 'fb-root'}),
          (('div',), {'class': 'flex-video'}),
          (('div',), {'class': 'storify'}),
          (('div',), {'id': 'szohir-444mozi'}),
          (('h2',), {'class': 'szohir-444mozi'}),
          (('h2',), {'class': 'szohir-jo2kampany'}),
          (('h2',), {'class': 'szohir-tldr'}),
          (('h2',), {'class': 'ad-insighthungary'}),
          (('h2',), {'class': 'ad-johirlevel'}),
          (('ul',), {'class': 'pagination'}),
          (('div',), {'class': 'pagination'}),
          (('div',), {'class': 'nls-layout nls-box'}),
          (('style',), {}),
          (('div',), {'class': 'pagination'}),
          (('div',), {'class': 'livestream__featured-list'}),
          (('div',), {'class': 'show-md'}),
          (('a',), {'class': 'pr-box'}),    #??

          ]
# <aside data-load-type=noop data-panelmod-type=relatedContent data-role=@STYLE>
# <a class=pr-box pr-box--compact pr-box--centered href=@LINK>
# 'tovább'-os, kellhet https://444.hu/2014/09/15/orban-viktor-visszaadja-a-bankok-penzet-az-embereknek
#<div class=row between-xs livestream>
MEDIA_LIST = [(('div',), {'id': 'bodyContent'}),  # 1 db wikipedia cikk
              (('div',), {'id': 'mw-content-text'}),
              (('figure',), {}),
              (('iframe',), {}),
              (('object',), {}),  # ????
              (('video',), {}),  # ????
              (('div',), {'class': 'embedly-card'}),  # ????
              (('div',), {'class': 'fb-video'}),
              (('div',), {'class': 'fb-post'}),
              (('blockquote',), {'class': 'twitter-tweet'}),
              (('blockquote',), {'class': 'instagram-media'}),
              (('blockquote',), {'class': 'twitter-video'}),
              (('svg',), {'id': 'Layer_1'}),
              (('svg',), {'class': 'meszaros-orban'}),
              (('defs',), {}),
              (('div',), {'class': 'whitebox'})]


def decompose_spec(article_dec):
    # from 2020: <a class="pr-box pr-box--compact pr-box--centered" href="https://membership.444.hu">
    for h2 in article_dec.find_all('h2'):
        for a in h2.find_all('a', {'href': 'direkt36_spec'}):
            print(h2)
            a.decompose()
    decompose_listed_subtrees_and_mark_media_descendants(article_dec, DECOMP, MEDIA_LIST)

    return article_dec


BLACKLIST_SPEC = ['https://444.hu/2021/02/19/az-szfe-s-hallgatok-tobb-mint-otode-passzivaltatott-lehet-hogy-kesobb-vissza-se-mehetnek-a-kepzesukbe']
LINK_FILTER_SUBSTRINGS_SPEC = re.compile('|'.join(['LINK_FILTER_DUMMY_STRING']))

MULTIPAGE_URL_END = re.compile(r'.*\?page=.*')  # Dummy


def next_page_of_article_spec(curr_html):
    bs = BeautifulSoup(curr_html, 'lxml')
    next_page_cont1 = bs.find('li', class_='arrow')
    next_page_link2 = bs.find('a', {'class': 'page-link', 'aria-label': 'Következő »'})
    if next_page_cont1 is not None:
        next_page_link = next_page_cont1.find('a', href=True)
        if next_page_link is not None and next_page_link.text.startswith('Következő'):
            return next_page_link.attrs['href']
        return None
    elif next_page_link2 is not None:
        return next_page_link2.attrs['href']
    return None

#2022-01-25 18:05:21,171 WARNING: https://444.hu/2014/10/26/tuntetes-az-internetado-ellen-elo?reverse=1&page=3: AUTHOR TAG NOT FOUND!
# https://444.hu/post/90b775c8c2f830d284c08ac379ba216b   body
# https://444.hu/2015/05/23/gyere-boggie-gyere-europa-nem-veheti-el-toled-az-aranyermet?reverse=1&page=9 autjor

# https://444.hu/2018/06/27/brazilia-eselyeshez-meltoan-daralta-be-es-ejtette-ki-a-szerbeket   <table ?
#https://444.hu/2013/04/17/gyanusitott-lett-a-fideszes-kepviselo-fiat-segito-dekan   main
# https://444.hu/2019/12/17/az-alapjogi-biztos-soron-kivuli-vizsgalatot-indit-a-gyori-gyerekgyilkossag-ugyebe <div class=pr-box__info>
#https://444.hu/2015/11/16/orban-viktor-europat-megtamadtak-elo <main class=@smallNUM columns id=content-main>
# 2022-01-11 17:26:31,543 WARNING: https://444.hu/2014/07/08/megallithatja-e-barki-a-gepezetet-2?reverse=1&page=3: AUTHOR TAG NOT FOUND!
# 2022-01-11 17:26:31,543 WARNING: https://444.hu/2014/07/08/megallithatja-e-barki-a-gepezetet-2?reverse=1&page=3: SECTION TAG NOT FOUND!
# 2022-01-11 17:25:20,937 ERROR: TEI validation error: https://444.hu/2014/07/17/lezuhant-egy-malaj-utasszallito-ukrajna-felett?reverse=1&page=2 50ea8216-4e96-5be0-9d59-eea71deb5554.xml Did not expect element p there, line 356
"""Traceback (most recent call last):
  File "/usr/lib/python3.8/runpy.py", line 194, in _run_module_as_main
    return _run_code(code, main_globals, None,
  File "/usr/lib/python3.8/runpy.py", line 87, in _run_code
    exec(code, run_globals)
  File "/home/eltedh/PycharmProjects/HTML2TEI/src/html2tei/__main__.py", line 129, in <module>
    entrypoint()
  File "/home/eltedh/PycharmProjects/HTML2TEI/src/html2tei/__main__.py", line 119, in entrypoint
    run_main(*common_args[:-1], command_dict[command][0], args, logfile_level=common_args[-1],
  File "/home/eltedh/PycharmProjects/HTML2TEI/src/html2tei/processing_utils.py", line 206, in run_main
    for publish_date in run_fun(warc_level_params, log_file_names_and_modes, process_article_fun,
  File "/home/eltedh/PycharmProjects/HTML2TEI/src/html2tei/processing_utils.py", line 118, in run_multiple_process
    yield after_function(ret, after_params, fhandles)
  File "/home/eltedh/PycharmProjects/HTML2TEI/src/html2tei/portal_article_cleaner.py", line 282, in after_clean
    final_filename = validator_hasher_compressor.process_one_file(url, desired_filename, filename_suff, tei_string)
  File "/home/eltedh/PycharmProjects/HTML2TEI/src/html2tei/validate_hash_zip.py", line 165, in process_one_file
    xml_etree = etree.fromstring(raw_xml_str)
  File "src/lxml/etree.pyx", line 3252, in lxml.etree.fromstring
  File "src/lxml/parser.pxi", line 1912, in lxml.etree._parseMemoryDocument
  File "src/lxml/parser.pxi", line 1800, in lxml.etree._parseDoc
  File "src/lxml/parser.pxi", line 1141, in lxml.etree._BaseParser._parseDoc
  File "src/lxml/parser.pxi", line 615, in lxml.etree._ParserContext._handleParseResultDoc
  File "src/lxml/parser.pxi", line 725, in lxml.etree._handleParseResult
  File "src/lxml/parser.pxi", line 654, in lxml.etree._raiseParseError
  File "<string>", line 280
lxml.etree.XMLSyntaxError: XML declaration allowed only at the start of the document, line 280, column 10"""
# utolsó: 2022-01-25 20:02:04,912 WARNING: https://444.hu/2014/06/29/ma-egy-csapat-biztosan-tortenelmet-ir?reverse=1&page=6: AUTHOR TAG NOT FOUND!