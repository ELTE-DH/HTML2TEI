#!/usr/bin/env python3
# -*- coding: utf-8, vim: expandtab:ts=4 -*

import re

from bs4 import BeautifulSoup

from html2tei import parse_date, BASIC_LINK_ATTRS, decompose_listed_subtrees_and_mark_media_descendants, tei_defaultdict

PORTAL_URL_PREFIX = 'https://merce.hu'

ARTICLE_ROOT_PARAMS_SPEC = [(('div',), {'class': 'entry-content'})]  #


def get_meta_from_articles_spec(tei_logger, url, bs):
    data = tei_defaultdict()
    data['sch:url'] = url
    # CSAK POST https://merce.hu/pp/2019/05/24/dk-s-es-lmp-s-kampanyzaro-ir-es-cseh-valasztas-az-ep-valasztas-masodik-napjan-percrol-percre-a-mercen/az-lmp-vekkeres-performansszal-es-almaosztassal-zarta-ep-kampanyat/
    # <a href="https://merce.hu/2019/05/24/dk-s-es-lmp-s-kampanyzaro-ir-es-cseh-valasztas-az-ep-valasztas-masodik-napjan-percrol-percre-a-mercen/" class="pplive__header-fulllink">
    if bs.find('a', {'class': 'pplive__header-fulllink'}) is not None:
        tei_logger.log('DEBUG', f'{url}: FEED POST!')
        return None
    main_pub_date_tag = bs.find('div', {'class': 'meta-time'})
    if main_pub_date_tag is not None:
        date_tag = main_pub_date_tag.find('time', {'datetime': True})
        if date_tag is not None:
            parsed_date = parse_date(date_tag.attrs['datetime'][:19], '%Y-%m-%dT%H:%M:%S')
            data['sch:datePublished'] = parsed_date
        else:
            tei_logger.log('WARNING', f'{url}: DATE FORMAT ERROR!')
    else:
        date_tag = bs.find('meta', {'property': 'article:published_time', 'content': True})
        if date_tag is not None:
            parsed_date = parse_date(date_tag.attrs['content'][:19], '%Y-%m-%dT%H:%M:%S')
            data['sch:datePublished'] = parsed_date
        else:
            tei_logger.log('WARNING', f'{url}: DATE TAG NOT FOUND!')
    #data['sch:dateModified'] = write_it
    # else: tei_logger.log('WARNING', f'{url}: MODIFIED DATE TEXT FORMAT ERROR!')
    title = bs.find('h1', {'class': 'entry-title'})
    if title is not None:
        data['sch:name'] = title.text.strip()
    else:
        if bs.find('div', class_='wp-block-group__inner-container'):
            ferge = bs.find('h2')
            if ferge is not None:
                data['sch:name'] = ferge.text.strip()
        else:
            tei_logger.log('WARNING', f'{url}: TITLE NOT FOUND IN URL!')
    authors_cont = bs.find('h1', {'data-act': 'author'})
    if authors_cont is not None:
        authors = [author.text.strip for author in authors_cont.find_all('a')]
        if len(authors) > 0:
            data['sch:author'] = authors
            if len(authors) > 1:
                print('Több szerző', url)
    # TODO: mérce vendégszerző, név a cikk alján: https://merce.hu/2017/09/01/megmentheti-e_emmanuel_macron_a_kelet-europaiakat_a_kizsakmanyolastol/
    # else: tei_logger.log('WARNING', f'{url}: AUTHOR TAG NOT FOUND!')
    # <div class="featured-tag">
    """is_section = bs.find('div', {'class': 'featured-tag'})
    if is_section is not None:
        data['sch:articleSection'] = is_section.text.strip() #[is_section.text.strip()]
    else:
        tei_logger.log('WARNING', f'{url}: SECTION TAG NOT FOUND!')"""
    # <ul class="tag-links"><li><a href="https://merce.hu/tag/orban_viktor/"
    tag_links = bs.find('ul', {'class': 'tag-links'})
    if tag_links is not None:
        tags = [tag.text.strip() for tag in tag_links.find_all('a')]
        if len(tags) > 0:
            data['sch:keywords'] = tags
    else:
        tei_logger.log('DEBUG', f'{url}: TAGS NOT FOUND!')
    # class="track-act post-tag-orban_viktor" data-act="tag">Orbán Viktor</a></li><li>
    # <a href="https://merce.hu/tag/kormany/" class="track-act post-tag-kormany" data-act="tag">kormány</a></li>

    # <li><a href="https://merce.hu/tag/gazdasag/" class="track-act post-tag-gazdasag" data-act="tag">gazdaság</a>
    return data


# (via 444.hu, HVG.hu)  https://merce.hu/2021/04/19/modositja-a-kormany-az-unios-jogot-serto-ceu-t-eluldozo-felsooktatasi-torvenyt/


def excluded_tags_spec(tag):
    if tag.name == 'td':
        tag.attrs = {}
    return tag


BLOCK_RULES_SPEC = {}
BIGRAM_RULES_SPEC = {'szakasz': {('jegyz_jelzo', 'det_any_desc'): ('editorial_note', 'unwrap')},
                     'idezet': {('jegyz_jelzo', 'det_any_desc'): ('editorial_note', 'unwrap')},
                     'doboz': {('merce_gomb', 'det_any_desc'): ('editorial_note', 'unwrap'),
                               ('jegyz_jelzo', 'det_any_desc'): ('editorial_note', 'unwrap')}}
#   szakasz jegyz_jelzo
#   idezet jegyz_jelzo
#   doboz merce_gomb
# CSAK SZÖVEGRŐL: <p>Ha szívesen olvasol és nézel hasonló közvetítéseket, ttps://merce.hu/2021/07/31/elegedetlen-szakmai-szervezetek-es-meg-elegedetlenebb-dolgozok-a-jarvany-ota-eloszor-mentek-utcara-az-egeszsegugyi-dolgozok/ https://merce.hu/pp/2021/07/31/orszagszerte-tuntetnek-az-egeszsegugyi-szakdolgozok-percrol-percre-a-mercen/a-szakdolgozok-munkaja-szolgalat-de-nem-szolgasag/
# <p>Tudósításunk itt zárul,
LINKS_SPEC = {'a', '0_MDESC_a', 'img', '0_MDESC_img', 'iframe', '0_MDESC_iframe', 'param'}
DECOMP = []
# https://merce.hu/2022/06/15/londoni-civilek-blokadja-es-az-emberi-jogok-europai-birosaga-akadalyozta-meg-az-elso-ruandaba-torteno-kitoloncolast-angliabol/
# támogatás <div class="mrc-bnr-plchldr mrc-bnr-plc-article_inside mrc-bnr-plcd" data-place="article_inside" data-add-class="">
# NEM KUKA,ikább szerk. jegyz: <div class="mrc-bnr-plchldr mrc-bnr-plc-article_begin mrc-bnr-plcd"  de mindenhol az??
# támogass kattintós: https://merce.hu/2017/07/22/ne_ketsebesseges_hanem_kozos_europai_unioban_gondolkodjunk/
# <a href="http://kettosmerce.blog.hu/2014/12/06/tamogass_318" onclick="ga('blogCustomPrimaryGATracking.send', 'event', 'tamogatas-oldal', 'banner-click-cikkozepi', window.location.pathname);" target="_blank" rel="noopener"><img src="http://m.blog.hu/ke/kettosmerce/image/szazalek-banner-anim2.gif" alt="szazalek-banner-anim2.gif" class="imgnotext"></a>

MEDIA_LIST = []


def decompose_spec(article_dec):
    # TODO: https://merce.hu/2020/07/31/zenes-tuntetest-szerveznek-a-rendezvenyszektor-bajbajutottjaiert/
    # <div class="box">Ez a cikk több mint 2 éves.</div>
    # <div class="mrc-bnr-plchldr mrc-bnr-plc-article_begin mrc-bnr-plcd" data-place="article_begin" data-add-class=""><div class="mrc-bnr-inside"><h4 style="font-size: 14px; text-align: left;">A Mércét ingyen és reklámok nélkül olvashatod. Ezt az olvasóink támogatása biztosítja. Rád is szükségünk van. <a href="https://merce.hu/redirect/172878/">Támogass minket!</a></h4></div></di
    decompose_listed_subtrees_and_mark_media_descendants(article_dec, DECOMP, MEDIA_LIST)
    return article_dec


BLACKLIST_SPEC = []

# with complicated links, its best to use re.compile('|'.join([re.escape(s) for s in url_list]))
LINK_FILTER_SUBSTRINGS_SPEC = re.compile('|'.join(['LINK_FILTER_DUMMY_STRING']))

MULTIPAGE_URL_END = re.compile(r'^\b$')  # Dummy


def next_page_of_article_spec(curr_html):
    ret = None
    soup = BeautifulSoup(curr_html, 'lxml')
    next_page = soup.find('a', attrs={'data-act': 'load-more'})
    last_page = soup.select('div.pplive__loadmore-wrap.text-center.d-none')
    if next_page is not None and 'href' in next_page.attrs and len(last_page) == 0:
        # post url eg.: https://merce.hu/pp/2018/04/08/magyarorszag-valaszt/
        # lemondott-az-egyutt-teljes-elnoksege-a-part-jovoje-is-kerdeses/"
        # The next page link can be compiled from the page's own url and the 'loadall=1' from 'pars' (if it exists).
        # We can compile the main url from one of the posts url with truncating the end and the 'pp/' substring
        # which refers to the post.
        firstpost_tag = soup.find('a', {'data-act': 'pp-item-title', 'class': 'track-act', 'href': True})
        if firstpost_tag:
            post_url_cut = firstpost_tag['href'][0:-1].replace('pp/', '')
            url = post_url_cut[:post_url_cut.rfind('/')]
            pars = next_page.attrs['href']
            ret = f'{url}/{pars}'
        return ret
    return None
