#!/usr/bin/env python3
# -*- coding: utf-8, vim: expandtab:ts=4 -*

import re
from os.path import join as os_path_join, dirname as os_path_dirname, abspath as os_path_abspath

from bs4 import BeautifulSoup

from html2tei import parse_date, BASIC_LINK_ATTRS, decompose_listed_subtrees_and_mark_media_descendants, tei_defaultdict

PORTAL_URL_PREFIX = 'https://index.hu/24ora/?cimke=koronav%C3%ADrus'

ARTICLE_ROOT_PARAMS_SPEC = [(('div',), {'class': 'mindenkozben_post_content'}),  # Mindeközben
                            (('div',), {'class': 'pp-list main'}),  # Index reports
                            (('div',), {'class': 'cikk-torzs-container'}),  # Index, totalcar, totalbike
                            (('div',), {'class': 't-article-container_main'})]  # Dívány


def get_meta_from_articles_spec(tei_logger, url, bs):
    data = tei_defaultdict()
    data['sch:url'] = url
    if bs.find('div', class_='mindenkozben_post_content content'):
        # MINDEKÖZBEN: 'https://index.hu/mindekozben/poszt/2020/12/21/virusbiztos_pulcsi_karacsonyra/'
        data['sch:articleSection'] = 'Mindeközben'
        pub_date = bs.find('meta', {'name': 'i:publication'})
        if pub_date is not None:
            parsed_date = parse_date(pub_date.attrs['content'].strip(), '%Y. %m. %d.')
            if parsed_date is not None:
                data['sch:datePublished'] = parsed_date
            else:
                tei_logger.log('WARNING', f'{url}  UNKNOWN DATE FORMAT 1')
        else:
            tei_logger.log('WARNING', f'{url}  MISSING DATE')
        keyword = bs.find('div', class_='heading')
        if keyword is not None:
            data['sch:keywords'] = [keyword.text.strip()]
        author = bs.find('div', class_='name')
        if author is not None:
            data['sch:author'] = [author.text.strip()]
        else:
            tei_logger.log('WARNING', f'{url}: AUTHOR TAG NOT FOUND!')
        title = bs.find('h3', class_='title')
        if title is not None:
            data['sch:name'] = title.text.strip()
        else:
            tei_logger.log('WARNING', f'{url}: TITLE NOT FOUND IN URL!')
        return data

    elif 'https://index.hu/' in url or 'https://velvet.hu/' in url or 'https://totalcar.hu/' in url or \
            'https://totalbike.hu/' in url:
        # 'https://index.hu/techtud/2020/03/19/koronavirus_netflix_korlatozas_karanten_europai_unio/'
        # 'https://totalcar.hu/magazin/kozelet/2020/04/05/autozas_a_jarvany_utan_semmi_nem_lesz_olyan_mint_elotte/'
        # <div class="datum"><span>2020.03.19. 20:29</span>
        # <span class="modositas-datuma-gomb" title="Módosítás dátuma">Módosítva: 2020.03.19. 21:16</span></div>
        dates_tag = bs.find('div', class_='datum')
        if dates_tag is not None and len(dates_tag.text.strip()) > 0:
            for span in dates_tag.find_all('span'):
                if 'class' in span.attrs.keys() and (span.attrs['class'] == ['modositas-datuma-gomb']):
                    parsed_mod_date = parse_date(span.text.strip()[11:], '%Y.%m.%d. %H:%M')
                    if parsed_mod_date is not None:
                        data['sch:dateModified'] = parsed_mod_date
                    else:
                        tei_logger.log('WARNING', f'{url}  UNKNOWN MODIFIED DATE FORMAT')
                else:
                    parsed_date = parse_date(span.text.strip(), '%Y.%m.%d. %H:%M')
                    if parsed_date is not None:
                        data['sch:datePublished'] = parsed_date
                    else:
                        # <meta property="og:updated_time" content="2021-05-15T08:47:31+02:00
                        date_tag = bs.find('meta', {'property': 'og:updated_time'})
                        # <time class="updated" datetime="2019-12-27T13:31:40+01:00">
                        if date_tag is not None and 'content' in date_tag.attrs.keys():
                            parsed_date = parse_date(date_tag.attrs['content'][:19], '%Y-%m-%dT%H:%M:%S')
                            if parsed_date:
                                data['sch:datePublished'] = parsed_date
                            else:
                                tei_logger.log('WARNING', f'{url}  UNKNOWN DATE FORMAT 2')
                        else:
                            tei_logger.log('WARNING', f'{url}  MISSING DATE')
        else:
            post_pub_date = bs.find('span', class_='ido')
            if post_pub_date is not None:
                parsed_date = parse_date(post_pub_date.text.strip(), '%Y. %B %d., %H:%M')    # 2020. április  1., 11:53
                if parsed_date is not None:
                    data['sch:datePublished'] = parsed_date
                else:
                    # <meta property="og:updated_time" content="2021-05-15T08:47:31+02:00
                    date_tag = bs.find('meta', {'property': 'og:updated_time'})
                    # <time class="updated" datetime="2019-12-27T13:31:40+01:00">
                    if date_tag is not None and 'content' in date_tag.attrs.keys():
                        parsed_date = parse_date(date_tag.attrs['content'][:19], '%Y-%m-%dT%H:%M:%S')
                        if parsed_date:
                            data['sch:datePublished'] = parsed_date
                        else:
                            tei_logger.log('WARNING', f'{url}  UNKNOWN DATE FORMAT 3b')
                    else:
                        tei_logger.log('WARNING', f'{url}  MISSING DATE')
            # <span class="ido" data-timestamp="1585734801000"></span>
            else:
                tei_logger.log('WARNING', f'{url}  MISSING DATE')
        if 'index' in url:
            if bs.find('div', class_='pp-list') is not None:
                # Reports: https://index.hu/belfold/2020/04/01/koronavirus_hirek_aprilis_1/
                title_container = bs.find('div', class_='content-title')
                if title_container is not None:
                    subtitle = title_container.find('h1', class_='alcim')
                    if subtitle is not None:
                        data['sch:alternateName'] = subtitle.text.strip()
                        main_title = title_container.find('h2')
                        if main_title is not None:
                            data['sch:name'] = main_title.text.strip()
                    else:
                        data['sch:name'] = title_container.find('h1').text.strip()

            else:   # Simple index.hu article
                title = bs.find('div', class_='content-title')
                if title is not None:
                    main_title = title.find('h1')
                    if main_title is not None:
                        data['sch:name'] = main_title.text.strip()
                    subtitle = title.find(class_='alcim')
                    if subtitle is not None:
                        data['sch:alternateName'] = subtitle.text.strip()
                else:
                    title = bs.find('h3', class_=['podcast-title', 'title default'])
                    # <h3 class="title default"> post címe
                    if title is not None:
                        data['sch:name'] = title.text.strip()
                    else:
                        title = bs.find('div', class_='_8z50')  # the warc does not contain it
                        if title is not None:
                            data['sch:name'] = title.text.strip()
                        #  https://index.hu/belfold/2020/05/15/kibeszelo_home_office_koronavirus_elo_adas_facebook_live/
                        else:   # <meta property="og:title" content="Majdnem 12 ezren vannak még karanténban" />
                            title = bs.find('meta', {'property': 'og:title', 'content': True})
                            if title is not None:
                                data['sch:name'] = title.attrs['content'].strip()
                            else:
                                tei_logger.log('WARNING', f'{url}: TITLE NOT FOUND IN URL!')
        else:   # VELVET
            # 'https://velvet.hu/gumicukor/2020/03/08/lakatos_mark_milanoi_divathet/'
            title = bs.find('h1')
            if title is not None:
                data['sch:name'] = title.text.strip()
            else:
                tei_logger.log('WARNING', f'{url}: TITLE NOT FOUND IN URL!')

        authors = [a.text.strip() for a in bs.find_all('a', rel='author')]
        if len(authors) > 0:
            data['sch:author'] = authors
        else:
            authors = [a.text.strip() for a in bs.find_all('div', class_='szerzo')]
            if authors is not None:
                data['sch:author'] = authors
            else:
                authors = [a.text.strip() for a in bs.find_all('div', class_='c-human_details_infos')]
                if len(authors) > 0:
                    data['sch:author'] = authors
                else:
                    post_author = bs.find('div', class_='name')  # közvetítés post
                    if post_author is not None:
                        data['sch:author'] = [post_author.text.strip()]
                    else:
                        tei_logger.log('WARNING', f'{url}: AUTHOR TAG NOT FOUND!')

        cimkek = bs.find('ul', class_=["cikk-cimkek", "m-tag-list"])
        if cimkek is not None:
            tags = [a.text.strip() for a in cimkek.find_all('a', class_='cimke-rovat-light')]
            if len(tags) > 0:
                data['sch:keywords'] = tags
            else:
                tei_logger.log('WARNING', f'{url}: TAGS NOT FOUND!')
            if 'index.hu' in url:
                section = cimkek.find('a', class_='cimke-rovat')
                if section is not None:
                    data['sch:articleSection'] = section.text.strip()
                else:
                    tei_logger.log('WARNING', f'{url}: SECTION TAG NOT FOUND!')
            else:   # Velvet
                section = bs.find('meta', {'name': 'news_keywords'})
                # velvet: <meta name="news_keywords" content="Élet" />
                if section is not None:
                    data['sch:articleSection'] = section.attrs['content']
                else:
                    tei_logger.log('WARNING', f'{url}: SECTION TAG NOT FOUND!')
        else:
            tei_logger.log('WARNING', f'{url}: SECTION TAG NOT FOUND!')
        return data

    elif 'https://femina.hu/' in url:  # bs.find('header', class_='m-femina-header')
        # https://femina.hu/egeszseg/koronavirus-immunitas/
        title = bs.find('div', class_='cim')
        if title is not None:
            data['sch:name'] = title.text.strip()
        else:
            tei_logger.log('WARNING', f'{url}: TITLE NOT FOUND IN URL!')
        author_and_date = [li.text.strip() for li in bs.find_all('li', class_='article-meta-item')]
        if len(author_and_date) > 0:
            data['sch:author'] = [author_and_date[0]]
            pub_date_text = author_and_date[1]
            parsed_date = parse_date(pub_date_text, '%Y.%m.%d.')
            if parsed_date is not None:
                data['sch:datePublished'] = parsed_date
            else:
                tei_logger.log('WARNING', f'{url}  UNKNOWN DATE FORMAT 4')
        else:
            tei_logger.log('WARNING', f'{url}: AUTHOR TAG AND DATE CONTAINER NOT FOUND!')

        cimkek = bs.find('ul', class_="cikk-cimkek-list")
        if cimkek is not None:
            tags = [a.text.strip() for a in cimkek.find_all('a', class_='cimke-rovat-light')]
            if len(tags) > 0:
                data['sch:keywords'] = tags[1:]
        section = cimkek.find('a', class_='cimke-rovat')
        if section is not None:
            data['sch:articleSection'] = section.text.strip()
        else:
            tei_logger.log('WARNING', f'{url}: TAGS AND SECTION NOT FOUND!')
        return data

    elif 'https://divany.hu/' in url:
        # index/divany: 'https://divany.hu/szuloseg/2020/04/16/jarvany-visszaeles-zaklatas'
        title = bs.find('h1', class_='t-article-head_text_title')
        if title is not None:
            data['sch:name'] = title.text.strip()
        else:
            title2 = bs.find('h2', class_='t-article-head_text_title')
            if title2 is not None:
                data['sch:name'] = title2.text.strip()
            else:
                tei_logger.log('WARNING', f'{url}: TITLE NOT FOUND!')
        authors = [a.text.strip() for a in bs.find_all('a', rel='author')]
        if len(authors) > 0:
            data['sch:author'] = authors
        else:
            authors2 = bs.find('a', class_='c-human_details_infos_name')
            if authors2 is not None:
                data['sch:author'] = [authors2.text.strip()]
            else:
                tei_logger.log('WARNING', f'{url}: AUTHOR TAG NOT FOUND!')
        date_tag = bs.find('time', class_='t-asd_share-date_date')  # datetime="2021-01-20T08:00:06+01:00
        if date_tag is not None and date_tag.get('datetime'):
            parsed_date = parse_date(date_tag.attrs['datetime'][:19], '%Y-%m-%dT%H:%M:%S')
            data['sch:datePublished'] = parsed_date  # date_tag.attrs['datetime']
        else:
            tei_logger.log('WARNING', f'{url}  MISSING DATE OR UNKONOWN DATE FORMAT')

        cimkek = bs.find('ul', class_="m-tags")
        if cimkek is not None:
            tags = [a.text.strip() for a in cimkek.find_all('a', class_='cimke-rovat-light')]
            if len(tags) > 0:
                data['sch:keywords'] = tags
            section = cimkek.find('a', class_='cimke-rovat')
            if section is not None:
                data['sch:articleSection'] = section.text.strip()
            else:
                tei_logger.log('WARNING', f'{url}: SECTION NOT FOUND!')
        else:
            tei_logger.log('WARNING', f'{url}: TAGS NOT FOUND!')
        return data


def excluded_tags_spec(tag):
    tag_attrs = tag.attrs
    if tag.name == 'a' and 'name' in tag_attrs.keys():
        tag_attrs['name'] = '@name'
    # <div class=esemeny-doboz serules @serulesNUM>
    elif tag.name == 'div':
        if 'data-aspect-ratio' in tag_attrs.keys():
            tag_attrs['data-aspect-rati'] = '@rat'
        elif 'class' in tag_attrs.keys() and 'esemeny-doboz' in tag_attrs['class']:
            tag_attrs['class'] = '@esemeny-doboz'

    return tag


BLOCK_RULES_SPEC = {'kviz': {'rename': {'lista': 'valaszblokk', 'listaelem': 'valasz'}}}
BIGRAM_RULES_SPEC = {'kviz': {('listaelem', 'det_by_any_desc'): ('kviz', 'valasz')}}
LINKS_SPEC = BASIC_LINK_ATTRS
DECOMP = [(('div',), {'id': 'microsite-microsite'}),
          (('div',), {'class': 'linkpreview'}),  # Kapcsolódó cikkek
          (('div',), {'class': 'cikk-bottom-text-ad'}),
          (('div',), {'class': 'cikk-inline-ad'}),
          (('div',), {'class': 'social-stripe'}),
          (('div',), {'class': 'szelso-jobb'}),
          (('div',), {'class': 'avatar'}),
          (('script',), {}),
          (('noscript',), {}),
          (('div',), {'class': 'h-miniapp-layout-right'}),
          (('div',), {'class': 't-article-container_sidebar'}),
          (('div',), {'class': 'h-miniapp-layout-article'}),
          (('div',), {'class': 'joautok-iframe-cikk-torzs'}),
          (('div',), {'class': 'social'}),
          (('div',), {'class': 'author-share-date-container'}),
          (('div',), {'class': 'cim'}),
          (('div',), {'data-miniapp-id': True}),
          (('div',), {'class': 'cikkvegi_dfp'}),
          (('div',), {'class': 'elozmenyek'}),
          (('div',), {'class': 'cikk-vegi-ajanlo-reklamok-container'}),
          (('div',), {'class': 'tabnavigation'}),
          (('div',), {'class': 'tab-right'}),
          (('div',), {'class': 't-article-info'}),
          (('ul',), {'class': 'm-tag-list'}),
          (('aside',), {}),
          (('div',), {'class': 'pagination'}),
          (('nav',), {'class': 'pagination'}),
          (('div',), {'class': 'nm_supported__wrapper'}),
          ]
# <div class=miniapp socialbox id=@STYLE>
MEDIA_LIST = []


def decompose_spec(article_dec):
    decompose_listed_subtrees_and_mark_media_descendants(article_dec, DECOMP, MEDIA_LIST)
    # 'mindeközben' titles
    if article_dec.find('div', class_='mindenkozben_post_content content'):
        article_dec.find('h3', class_='title').decompose()
    return article_dec


BLACKLIST_SPEC = [url.strip() for url in
                  open(os_path_join(os_path_dirname(os_path_abspath(__file__)), 'index_koronavirus_BLACKLIST.txt')).readlines()] + \
                 [url.strip() for url in
                  open(os_path_join(os_path_dirname(os_path_abspath(__file__)), 'index_BLACKLIST.txt')).readlines()] +\
                 [url.strip() for url in
                  open(os_path_join(os_path_dirname(os_path_abspath(__file__)), 'index_ROOT_ERROR.txt')).readlines()] \
                 + [url.strip() for url in
                  open(os_path_join(os_path_dirname(os_path_abspath(__file__)), 'index_UNICODEerror.txt')).readlines()] \
                 + [url.strip() for url in
                  open(os_path_join(os_path_dirname(os_path_abspath(__file__)), 'index_EMPTY.txt')).readlines()]

LINK_FILTER_SUBSTRINGS_SPEC = re.compile('|'.join(['LINK_FILTER_DUMMY_STRING']))

MULTIPAGE_URL_END = re.compile(r'.*/\?p=.*')

# https://index.hu/belfold/2020/02/29/eloben_kozvetitjuk_az_eddigi_legnagyobb_magyar_lottonyeremeny_kihuzasa/?p=1
# TODO https://velvet.hu/trend/noferfi1108/
# <nav class=pager default tobboldalas_cikk id=pager_bottom>


def next_page_of_article_spec(curr_html):
    bs = BeautifulSoup(curr_html, 'lxml')
    pages = bs.find('div', class_='pagination clearfix')
    if pages is not None:
        for p in pages.find_all('a', class_='next'):
            if 'rel' not in p.attrs.keys():
                link = p.attrs['href']
                return link
    else:
        pages_velvet = bs.find('a', {'data-page': True, 'class': 'next', 'href': True})
        if pages_velvet:
            link = pages_velvet['href']
            return link
        return None
