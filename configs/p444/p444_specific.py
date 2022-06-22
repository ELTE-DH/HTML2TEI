#!/usr/bin/env python3
# -*- coding: utf-8, vim: expandtab:ts=4 -*-

import re

from bs4 import BeautifulSoup
from os.path import join as os_path_join, dirname as os_path_dirname, abspath as os_path_abspath

from src.html2tei import parse_date, decompose_listed_subtrees_and_mark_media_descendants, tei_defaultdict

PORTAL_URL_PREFIX = 'https://444.hu/'
ARTICLE_ROOT_PARAMS_SPEC = [(('section',), {'id': 'main-section'})]

HIGHLIGHT = re.compile(r'.*highlight.*')
A_TAGS = {'a', '0_MDESC_a'}


def get_meta_from_articles_spec(tei_logger, url, bs):
    data = tei_defaultdict()
    data['sch:url'] = url
    dates_cont = []
    raw_meta = bs.find('div', {'id': 'headline'})
    title = bs.find('meta', {'name': 'title'})
    if title is not None:
        data['sch:name'] = title.text.strip()
    else:
        title = bs.find('h1')
        if title is not None:
            data['sch:name'] = title.text.strip()
        else:
            tei_logger.log('WARNING', f'{url}: TITLE NOT FOUND!')

    date_tag = bs.find('meta', property='article:published_time')  # 2021-05-11T19:31:11+02:00"
    if date_tag is not None:
        parsed_date = parse_date(date_tag.attrs['content'][:19], '%Y-%m-%dT%H:%M:%S')
        dates_cont.append(parsed_date)
    modified_date = bs.find('meta', property='article:modified_time').attrs['content']
    if modified_date is not None:
        parsed_moddate = parse_date(modified_date[:19], '%Y-%m-%dT%H:%M:%S')
        dates_cont.append(parsed_moddate)
    lead_tag = bs.find('meta', {'name': 'description'})
    if lead_tag is not None:
        lead_text = lead_tag.attrs['content'].strip()
        data['sch:abstract'] = lead_text

    authors_list = raw_meta.find(class_='byline__authors')
    if authors_list is not None:
        authors_list = [a.text.strip() for a in authors_list.find_all('a')]
        data['sch:author'] = authors_list
    else:
        authors_tag = bs.find_all(class_='report__author')
        if len(authors_tag) > 0:
            authors_list = [au.text.strip() for au in authors_tag]
            data['sch:author'] = authors_list
        else:
            # <a class="fS eD f4 eS eT eU eV f9 fg" href="/author/czinkoczis">Czinkóczi Sándor
            authors = [a.text.strip() for a in bs.find_all('a', {'href': re.compile("/author/.*")})]
            if len(authors) > 0:
                data['sch:author'] = authors
                print(url, authors)
            else:
                tei_logger.log('WARNING', f'{url}: AUTHOR TAG NOT FOUND!')

    section = raw_meta.find(class_='byline__category')
    if section is not None:
        data['sch:articleSection'] = section.text.strip()
    else:
        section = bs.find('meta', {'itemprop': 'articleSection'})
        if section is not None and 'content' in section.attrs.keys():
            data['sch:articleSection'] = section.attrs['content'].strip()
        else:
            tei_logger.log('DEBUG', f'{url}: SECTION TAG NOT FOUND!')
    keywords_root = bs.find('meta', {'name': 'keywords'})
    if keywords_root is not None:
        keywords_list = keywords_root.attrs['content'].split(',')
        data['sch:keywords'] = keywords_list
    else:
        tei_logger.log('DEBUG', f'{url}: KEYWORDS NOT FOUND!')
    lead_tag = bs.find('meta', {'name': 'description'})
    if lead_tag is not None:
        lead_text = lead_tag.attrs['content'].strip()
        data['sch:abstract'] = lead_text

    # https://444.hu/2015/11/16/orban-viktor-europat-megtamadtak-elo
    report_dates = bs.find_all('a', class_='report__date')
    if report_dates:
        if report_dates[0].find('div', class_='report__time'):  # 2016. 06. 14., kedd
            for one_date_tag in report_dates:
                datetime_str = ''
                for d in one_date_tag.contents:
                    d_str = d.text.strip()
                    if len(d_str) == 5:
                        datetime_str = d_str
                    elif len(d_str) > 5:
                        datetime_str = f'{d_str[0:13]} {datetime_str}'
                parsed_date = parse_date(datetime_str, '%Y. %m. %d. %H:%M')
                if parsed_date:
                    dates_cont.append(parsed_date)
        else:
            for rep in report_dates:    # '2014. október. 26., vasárnap, 19:57'
                rep_span = rep.find('span')
                if rep_span is not None:
                    parsed_rep_datetime = parse_date(rep_span.text.strip(), '%Y. %B. %d., %A, %H:%M')
                    if parsed_rep_datetime is not None:
                        dates_cont.append(parsed_rep_datetime)

    if len(dates_cont) > 0:
        data['sch:datePublished'] = min(dates_cont)
        if data['sch:datePublished'] != data['sch:dateModified']:
            data['sch:dateModified'] = max(dates_cont)
    else:
        tei_logger.log('WARNING', f'{url}: DATE NOT FOUND IN URL!')
    return data


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

LINKS_SPEC = {'a', '0_MDESC_a', 'img', '0_MDESC_img', 'iframe', '0_MDESC_iframe', 'blockquote'}
DECOMP = [(('div',), {'id': 'headline'}),
          (('div',), {'class': 'hide-print'}),
          (('div',), {'class': 'hide-for-print'}),
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
          (('a',), {'class': 'pr-box'}),  # ??
          (('div',), {'id': 'mc_embed_signup'})
          ]

MEDIA_LIST = [(('div',), {'id': 'bodyContent'}),  # 1 wikipedia cikk
              (('div',), {'id': 'mw-content-text'}),
              (('figure',), {}),
              (('iframe',), {}),
              (('object',), {}),
              (('video',), {}),
              (('div',), {'class': 'embedly-card'}),
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
    # after 2020: <a class="pr-box pr-box--compact pr-box--centered" href="https://membership.444.hu">
    for h2 in article_dec.find_all('h2'):
        for a in h2.find_all('a', {'href': 'direkt36_spec'}):
            print(h2)
            a.decompose()
    decompose_listed_subtrees_and_mark_media_descendants(article_dec, DECOMP, MEDIA_LIST)
    return article_dec


BLACKLIST_SPEC = [
    'https://444.hu/2021/02/19/az-szfe-s-hallgatok-tobb-mint-otode-passzivaltatott-lehet-hogy-kesobb-vissza-se'
    '-mehetnek-a-kepzesukbe',
    'https://444.hu/2015/05/23/amerika-ezentul-nem-gyujtheti-tomegesen-a-telefonhivasok-metaadatait',
    'https://444.hu/2015/05/23/kelet-europaban-nyitna-uj-gyarat-a-land-rover',
    'https://444.hu/2015/05/23/sajatjanak-hazudott-juhnyaj-utan-vett-fel-agrartamogatast-a-bekolcei-agrarbunozo'] + \
                 [url.strip() for url in
                  open(os_path_join(os_path_dirname(os_path_abspath(__file__)), '444_EMPTY_ARTICLES.txt')).readlines()]

LINK_FILTER_SUBSTRINGS_SPEC = re.compile('|'.join(['http://Az%20Index%20egy%C3%A9bk%C3%A9nt%20ezeket%20a%20k%C3%A9rd%C3%A9seket%20k%C3%BCldte%20el%20kedden%20az%20operat%C3%ADv%20t%C3%B6rzsnek:%20%20A%20s%C3%BCrg%C5%91ss%C3%A9gi%20ell%C3%A1t%C3%A1s%20%C3%BAj%20protokollja%20szerint%20csontt%C3%B6r%C3%A9sek%20eset%C3%A9n%20csak%20ny%C3%ADlt%20t%C3%B6r%C3%A9sekn%C3%A9l%20%C3%A9s%20s%C3%BAlyos%20esetekben%20v%C3%A9geznek%20helyre%C3%A1ll%C3%ADt%C3%B3%20m%C5%B1t%C3%A9teket.%20Jelenleg%20teh%C3%A1t%20%22sima%22%20v%C3%A9gtagt%C3%B6r%C3%A9s%20eset%C3%A9n%20nincs%20helyre%C3%A1ll%C3%ADt%C3%B3%20m%C5%B1t%C3%A9t?%20Mi%20sz%C3%A1m%C3%ADt%20s%C3%BAlyosnak?%20Nem%20okoz%20ez%20maradand%C3%B3%20eg%C3%A9szs%C3%A9groml%C3%A1st?%20Fenntartj%C3%A1k,%20hogy%20nem%20javasolj%C3%A1k%20a%20maszkvisel%C3%A9st%20mindenkinek,%20f%C5%91k%C3%A9nt%20azok%20ut%C3%A1n,%20hogy%20a%20minisztereln%C3%B6k%20a%20parlamentben%20azt%20mondta,%20val%C3%B3j%C3%A1ban%20mindenkinek%20hordania%20kellene,%20de%20nincs%20el%C3%A9g%20ebb%C5%91l%20Magyarorsz%C3%A1gon,%20nem%20tudj%C3%A1k%20biztos%C3%ADtani%20a%20lakoss%C3%A1gnak,%20ez%C3%A9rt%20nem%20lehet%20k%C3%B6telez%C5%91v%C3%A9%20tenni?%20A%20t%C3%B6bb%20mint%2013%20ezer%20magyarorsz%C3%A1gi%20mintav%C3%A9tel%20pontosan%20h%C3%A1ny%20emberen%20t%C3%B6rt%C3%A9nt%20meg?%20Konkr%C3%A9tan%20h%C3%A1ny%20embert%20teszteltek%20m%C3%A1r%20Magyarorsz%C3%A1gon%20a%20hat%C3%B3s%C3%A1gok%20az%20%C3%BAj%20koronav%C3%ADrussal,%20%C3%A9s%20egy%20esetben%20h%C3%A1nyszor%20kell%20mint%C3%A1t%20venni?%20%C3%81tlagosan%20napi%20ezer%20elv%C3%A9gzett%20mintav%C3%A9telt%20t%C3%BCntetnek%20fel,%20legal%C3%A1bbis%20az%20elm%C3%BAlt%20egy%20h%C3%A9tben,%20a%20kijel%C3%B6lt%20%C3%BAj%20laborokkal.%20Pontosan%20naponta%20h%C3%A1ny%20labortesztet%20v%C3%A9geznek%20a%20NNK%20k%C3%B6zponti%20laborj%C3%A1ban,%20%C3%A9s%20h%C3%A1ny%20darab%20mintav%C3%A9telt%20%C3%A9rt%C3%A9kelnek%20ki%20a%20kijel%C3%B6lt%207%20laborban?%20Mennyivel%20t%C3%B6bb%20vagy%20kevesebb%20a%20k%C3%B3rh%C3%A1zakban%20s%C3%BAlyos%20t%C3%BCd%C5%91gyullad%C3%A1ssal%20kezeltek%20sz%C3%A1ma%20az%20%C3%A9vnek%20ebben%20a%20szakasz%C3%A1ban%20megszokott%20%C3%A1tlagos%20adatokhoz%20k%C3%A9pest?%20Minden%20t%C3%BCd%C5%91gyullad%C3%A1sos%20t%C3%BCnettel,%20vagy%20%C3%A9pp%20konkr%C3%A9tan%20t%C3%BCd%C5%91gyullad%C3%A1ssal%20k%C3%B3rh%C3%A1zban%20fekv%C5%91%20betegn%C3%A9l%20elv%C3%A9gzik%20a%20koronav%C3%ADrus-tesztet%20a%20jelenlegi%20elj%C3%A1r%C3%A1srend%20szerint?%20N%C3%A1lunk%20nem%20volt%20kiugr%C3%B3%20n%C3%B6veked%C3%A9s%20a%20t%C3%BCd%C5%91gyullad%C3%A1sos,%20influenz%C3%A1s%20megbeteged%C3%A9sek%20sz%C3%A1m%C3%A1ban%20a%20koronav%C3%ADrus%20hivatalos%20megjelen%C3%A9se%20el%C5%91tt?',
                                                   'http://Az',
                                                   'https://www.w3.org/1999/xlink',
                                                   'Fot',
                                                   'mailto:<blockquote%20class=%22instagram-media%22%20data-instgrm'
                                                   ]))

#
MULTIPAGE_URL_END = re.compile(r'.*(\?|&)page=.*')


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

