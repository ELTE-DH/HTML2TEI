#!/usr/bin/env python3
# -*- coding: utf-8, vim: expandtab:ts=4 -*

import re
import ast
from collections import defaultdict
from bs4 import BeautifulSoup

from src.html2tei import parse_date, BASIC_LINK_ATTRS, decompose_listed_subtrees_and_mark_media_descendants, \
    tei_defaultdict, create_new_tag_with_string

PORTAL_URL_PREFIX = 'https://telex.hu'

ARTICLE_ROOT_PARAMS_SPEC = [(('div',), {'class': 'article_container_'})]


def get_meta_from_articles_spec(tei_logger, url, bs):
    data = tei_defaultdict()
    data['sch:url'] = url

    article_root = bs.find('div', id='cikk-content')
    if article_root:
        date_tag = bs.find('meta', {'name': 'article:published_time'})
        if date_tag is not None and 'content' in date_tag.attrs.keys():
            parsed_date = parse_date(date_tag.attrs['content'][:19], '%Y-%m-%dT%H:%M:%S')
            data['sch:datePublished'] = parsed_date
        else:
            tei_logger.log('WARNING', f'{url}: DATE TAG NOT FOUND!')
        date_mod_tag = bs.find('meta', {'name': 'article:modified_time'})
        if date_mod_tag is not None and 'content' in date_tag.attrs.keys():
            parsed_mod_date = parse_date(date_mod_tag.attrs['content'][:19], '%Y-%m-%dT%H:%M:%S')
            data['sch:dateModified'] = parsed_mod_date
        title = article_root.find('h1')
        if title is not None:
            data['sch:name'] = title.text.strip()
        else:
            tei_logger.log('WARNING', f'{url}: TITLE NOT FOUND IN URL!')
        subtitle = article_root.find('h2')
        if subtitle is not None:
            subtitle_text = subtitle.text.strip()
            if len(subtitle_text) > 0:
                data['sch:alternateName'] = subtitle_text
        authors = [author.text.strip() for author in article_root.find_all('a', class_='author__name')]
        post_authors = []  # authors of news feed
        for p_auth_tag in article_root.find_all('div', class_='article_author'):
            p_auth = p_auth_tag.find('em')
            if p_auth is not None:
                post_authors.append(p_auth.text.strip())
        if len(post_authors) > 0:
            authors.extend(list(set(post_authors)))
        if len(authors) > 0:
            data['sch:author'] = authors
        elif len(authors) > 1:
            tei_logger.log('WARNING', f'{url}: AUTHOR TAG NOT FOUND!')
        tags = [a.attrs['content'] for a in bs.find_all('meta', {'name': 'article:tag'})]
        if len(tags) > 0:
            data['sch:articleSection'] = tags[0]
        if len(tags) > 1:
            tags.remove(tags[0])
            data['sch:keywords'] = tags
        else:
            tei_logger.log('DEBUG', f'{url}: TAGS NOT FOUND!')
        return data
    tei_logger.log('WARNING', f'{url}: ARTICLE BODY NOT FOUND!')
    return None


def excluded_tags_spec(tag):
    return tag


BLOCK_RULES_SPEC = {}
BIGRAM_RULES_SPEC = {'kozvetites_content': {('cimsor', 'det_by_any_desc'): ('to_unwrap', 'cimsor')}}
LINKS_SPEC = BASIC_LINK_ATTRS
DECOMP = [(('div',), {'class': 'sidebar_container_'}),
          (('div',), {'class': 'top-section'}),
          (('div',), {'class': 'info-spacing-article'}),
          (('div',), {'class': 'article-bottom'}),
          (('div',), {'class': 'recommendation-block'}),
          (('div',), {'class': 'pagination'}),
          (('div',), {'class': 'recommendation'}),
          (('p',), {'class': 'adfree'})
          ]


MEDIA_LIST = []


def decompose_spec(article_dec):
    news_offerer = article_dec.find('a', text='A Telex legfrissebb híreit itt olvashatja')
    if news_offerer is not None:
        news_offerer.decompose()
    decompose_listed_subtrees_and_mark_media_descendants(article_dec, DECOMP, MEDIA_LIST)
    return article_dec


BLACKLIST_SPEC = []

MULTIPAGE_URL_END = re.compile(r'.*oldal=.')
LINK_FILTER_SUBSTRINGS_SPEC = re.compile('|'.join(['https://alapjarat.hu/aktualis/elfogyott-shell-v-power-95-sok'
                                                   '-hazai-kuton?utm_source%3_Dtelex&amp;utm_medium=article&amp'
                                                   ';utm_campaign=kifogyott_premium_uzemanyag']))


def next_page_of_article_spec(curr_html):  # https://telex.hu/koronavirus/2020/11/12/koronavirus-pp-2020-11-12/elo
    bs = BeautifulSoup(curr_html, 'lxml')
    if bs.find('div', class_='pagination') is not None:
        current_pagenum = int(bs.find('a', class_='current-page').attrs['href'][-1])
        for pagelink in bs.find_all('a', class_='page'):
            if pagelink.attrs['class'] != ['page', 'current-page']:
                href = pagelink.attrs['href']
                if href[-1].isdigit() and int(href[-1]) == current_pagenum + 1:
                    next_page = f'https://telex.hu{href}'
                    return next_page
    return None


def transform_to_html(url, raw_html, warc_logger):
    _ = url, warc_logger
    soup = BeautifulSoup(raw_html, 'html.parser')
    report_root = soup.find('div', {'id': 'liveblog-items-container'})
    root = soup.find('div', {'class': 'article-html-content'})
    if report_root is not None and len(root.text) < 60:
        return hibrid_builder(url, soup)
    return raw_html


def hibrid_builder(url, html_soup):
    reports = extract_sections_content_from_raw_html(html_soup)
    reports_root = html_soup.find('div', {'id': 'liveblog-items-container'})
    for report in reports:
        report_tag = html_soup.new_tag('report')
        for k, v in report.items():
            create_new_tag_with_string(html_soup, v, k, report_tag)
        reports_root.append(report_tag)
    return str(html_soup)


def extract_sections_content_from_raw_html(soup):
    # fn recieves a raw_html.
    # splits it into matches of individual post sections
    last_script = soup.find(lambda tag: tag.name == 'script' and not tag.attrs)
    script_tag_text = last_script.get_text(strip=True)
    if script_tag_text is None:
        return []

    regex_for_kozv_section_a = r"\{type:a,document:(.*?)\}\}"
    regex_for_kozv_section_b = r"\{type:b,document:(.*?)\}\}"
    regex_for_title = r"(?<=,title:)(.*?)(?=,pubDate)"
    regex_for_slug = r"(?<=,slug:)(.*?)(?=,articleAuthors:)"
    regex_for_content = r"(?<=,content:)(.*?)(?=,tags:)"
    regex_for_author = r"(?<=,name:)(.*?)(?=,email:)"

    def _run_match(section_regex):
        section_matches = re.finditer(section_regex, script_tag_text, re.MULTILINE | re.DOTALL)
        section_list = []
        for match in section_matches:
            for groupNum in range(0, len(match.groups())):
                match_dict = defaultdict(str)
                section_tag_text = match.group(1) + "}"

                # POST TITLE EXTRACTION
                post_title_match = re.search(regex_for_title, section_tag_text).group(0)
                # title not included in few cases, but "slug:title-text-with-dashes" is always present
                if post_title_match[0] != '"':
                    slug_match = re.search(regex_for_slug, section_tag_text).group(0)
                    post_title_match = ' '.join(slug_match.split('-')).capitalize()
                if post_title_match[0] == '"' and post_title_match[-1] == '"':
                    match_dict['post_title'] = post_title_match[1:-1]  # take " from both ends
                else:
                    match_dict['post_title'] = post_title_match

                # CONTENT EXTRACTION
                content_string_with_escapes = re.search(regex_for_content, section_tag_text).group(0)
                try:
                    content_string = ast.literal_eval(content_string_with_escapes)  # interprets escape characters
                    match_dict['post_content'] = content_string
                except ValueError:  # malformed node in cases where content is 'aB'
                    pass

                # AUTHOR EXTRACTION
                author_text = re.search(regex_for_author, section_tag_text).group(0)
                if author_text[0] == '"' and author_text[-1] == '"':
                    match_dict['post_author'] = author_text[1:-1]  # take " from both ends

                # only append if data was extracted
                if len(match_dict.keys()) > 0:
                    section_list.append(match_dict)

        # returns as list of dicts
        return section_list

    created_section_list = _run_match(regex_for_kozv_section_a)

    # run again with alternative section split regex
    if len(created_section_list) == 0:
        created_section_list = _run_match(regex_for_kozv_section_b)

    # return empty list if nothing could be extracted
    if len(created_section_list) == 0:
        return []

    return created_section_list
