#!/usr/bin/env python3
# -*- coding: utf-8, vim: expandtab:ts=4 -*

import re

from bs4 import Tag, BeautifulSoup
from os.path import join as os_path_join, dirname as os_path_dirname, abspath as os_path_abspath

from html2tei import parse_date, decompose_listed_subtrees_and_mark_media_descendants, tei_defaultdict

PORTAL_URL_PREFIX = 'http://valasz.hu'
ARTICLE_ROOT_PARAMS_SPEC = [(('article',), {'class': 'cikk-body'}), (('section',), {'class': 'cikk-percrol-percre'}),
                            (('article',), {'class': 'cikk-percrol-percre'})]


def get_meta_from_articles_spec(tei_logger, url, bs):
    data = tei_defaultdict()
    data['sch:url'] = url
    article_root = bs.find('article', class_='cikk-body')
    for args, kwargs in ARTICLE_ROOT_PARAMS_SPEC:
        article_root = bs.find(*args, **kwargs)
        if article_root is not None:
            break
    if article_root is not None:  # Date: <span class="datum">/ 2014.12.15., hétfő 11:45 /</span>
        date_tag = bs.find('span', class_='datum').text.strip()
        if date_tag is not None:
            date_text = date_tag[2:-2]
            if date_tag[2] == '2':
                parsed_date = parse_date(date_text, '%Y.%m.%d., %A %H:%M')
                if parsed_date is not None:
                    data['sch:datePublished'] = parsed_date
                else:
                    tei_logger.log('WARNING', f'{url}: DATE FORMAT ERROR!')
            else:
                tei_logger.log('WARNING', f'{url}: NOT REAL DATE ERROR!')
        else:
            tei_logger.log('WARNING', f'{url}: DATE TAG NOT FOUND!')
        article_title = article_root.find('h1', itemprop='name')
        if article_title is not None:
            data['sch:name'] = article_title.text.strip()
        else:
            tei_logger.log('WARNING', f'{url}: TITLE NOT FOUND IN URL!')
        article_subtitle = article_root.find('h2')
        if article_subtitle is not None:
            article_subtitle_text = article_subtitle.text.strip()
            if len(article_subtitle_text) > 0 and article_subtitle_text != '-':
                data['sch:alternateName'] = article_subtitle_text
        #  <span class="szerzo"><a class="szerzo" href="/szerzo/ujsagiro/-1656" rel="author"></a></span>
        #  <span class="datum"> | 2014.10.12., vasárnap 19:10 |</span>
        #  <span class="forras">Hírforrás: Válasz.hu</span>
        author_tags = article_root.find_all('a', rel='author')
        if len(author_tags) > 0:
            if any(len(elem.text.strip()) == 0 for elem in author_tags):
                source = article_root.find('span', class_="forras")
                if source is not None:
                    data['sch:source'] = source.text.strip()
            else:
                data['sch:author'] = [a.text for a in author_tags]
        else:
            # The source and author fields can co-exist
            article_source = article_root.find('span', class_='forras')
            article_author2 = article_root.find('span', class_='szerzo')
            if article_source is not None:
                data['sch:source'] = article_source.text.strip()
            if article_author2 is not None:
                data['sch:author'] = [article_author2.text.strip()]
        keyword_root = bs.find('aside', class_='breadcrumb')
        if keyword_root is not None:
            a_list = [a.text.strip() for a in keyword_root.find_all('a')]
            # a_list[0] contains 'Főoldal' therefore omitted
            data['sch:articleSection'] = a_list[1]
            if len(a_list) == 4:
                data['subsection'] = a_list[2]
        return data
    else:
        tei_logger.log('WARNING', f'{url}: ARTICLE BODY NOT FOUND!')
        return None


def excluded_tags_spec(tag):
    return tag


BLOCK_RULES_SPEC = {}

BIGRAM_RULES_SPEC = {'table_text': {('keretes_foto', 'det_by_any_desc'): ('media_tartalom', 'forras'),
                                    ('media_tartalom', 'det_by_any_desc'): ('doboz', 'media_tartalom'),
                                    ('keretes_kep_bigram', 'det_by_any_desc'): ('media_tartalom', 'bekezdes')},
                     'kviz_div': {('listaelem', 'det_by_any_desc'): ('kviz_div', 'kviz'),
                                  ('lista', 'det_by_any_desc'): ('kviz_div', 'to_unwrap')}}


LINKS_SPEC = {'a', '0_MDESC_a', 'img', '0_MDESC_img', 'iframe', '0_MDESC_iframe', 'embed', 'div'}

DECOMP = [(('script',), {}),
          (('noscript',), {}),
          (('footer',), {}),
          (('section',), {'class': 'rosta'}),
          (('section',), {'class': 'rosta cikk lista'}),
          (('section',), {'class': 'right-column'}),
          (('div',), {'class': 'head-cont'}),
          (('div',), {'class': 'clear-both'}),
          (('div',), {'class': 'socials footer'}),
          (('div',), {'class': ['socials', 'bottom']}),
          (('div',), {'class': 'socials'}),
          (('div',), {'class': 'article-merokod'}),
          (('div',), {'class': 'toolbar'}),
          (('h1',), {'itemprop': 'name'}),
          (('div',), {'class': 'buttons'}),
          # (('p',), {'class': 'infos'}),
          (('div',), {'class': 'icons'}),
          (('div',), {'class': 'kapcsolodo-cikkek'}),
          (('div',), {'class': 'footer-bottom'}),
          (('0_MDESC_div',), {'class': 'footer-bottom'}),
          (('div',), {'class': 'print-lap-ajanlo'}),
          ]


MEDIA_LIST = [
    (('blockquote',), {'class': 'twitter-tweet'}),
    (('blockquote',), {'class': 'twitter-video'}),
    (('blockquote',), {'class': 'instagram-media'}),
    (('div',), {'class': 'fb-post'}),
    (('div',), {'class': 'fb-video'}),
    (('div',), {'class': 'article-image'})]


def decompose_spec(article_dec):
    decompose_listed_subtrees_and_mark_media_descendants(article_dec, DECOMP, MEDIA_LIST)
    for c in article_dec.children:
        if isinstance(c, Tag) and c.name == 'h2':
            c.decompose()
    publi = article_dec.find('div', class_='head')
    if publi is not None and publi.find('h3') is not None:
        publi.decompose()
    return article_dec


LINK_FILTER_SUBSTRINGS_SPEC = re.compile('|'.join(['LINK_FILTER_DUMMY_STRING']))

BLACKLIST_SPEC = [url.strip() for url in
                  open(os_path_join(os_path_dirname(os_path_abspath(__file__)), 'valasz_BLACKLIST.txt')).readlines()]

MULTIPAGE_URL_END = re.compile(r'.*?page=.')


def next_page_of_article_spec(curr_html):
    bs = BeautifulSoup(curr_html, 'lxml')
    if bs.find('article', class_='percro-percre-lista') is not None:
        next_tag = bs.find('a', rel='next')
        if next_tag is not None and 'href' in next_tag.attrs.keys():
            next_link = next_tag.attrs['href']
            link = f'http://valasz.hu{next_link}'
            return link
    return None
