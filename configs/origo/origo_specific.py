#!/usr/bin/env python3
# -*- coding: utf-8, vim: expandtab:ts=4 -*

import re

from html2tei import parse_date, decompose_listed_subtrees_and_mark_media_descendants, tei_defaultdict

PORTAL_URL_PREFIX = 'https://www.origo.hu/'

ARTICLE_ROOT_PARAMS_SPEC = [(('div',), {'class': 'o-section-main'})]


def get_meta_from_articles_spec(tei_logger, url, bs):
    data = tei_defaultdict()
    data['sch:url'] = url

    # format 1
    article_head_format_1 = bs.find('header', class_='article-head')
    if article_head_format_1 is not None:
        # format 1 title
        title = article_head_format_1.find('h1', class_='article-title')

        if title is not None:
            data['sch:name'] = title.text.strip()
            # print(f'{title.text.strip()}')
        else:
            tei_logger.log('WARNING', f'{url}: TITLE NOT FOUND IN URL!')  # WARNING
        # format 1 author and date published
        article_info = bs.find('div', class_='article-info')
        if article_info is not None:
            author = article_info.find('span', class_='article-author')
            if author is not None:
                data['sch:author'] = [author.text.strip()]
                # print(f'{[author.text.strip()]}')
            else:
                tei_logger.log('WARNING', f'{url}: AUTHOR TAG NOT FOUND!')  # WARNING
            date_tag = article_info.find('div', class_='article-date')
            if date_tag is not None and 'datetime' in date_tag.attrs.keys():
                parsed_date = parse_date(date_tag.attrs['datetime'], '%Y-%m-%dT%H:%M')
                data['sch:datePublished'] = parsed_date
                # print(f'{parsed_date}')
            else:
                tei_logger.log('WARNING', f'{url}: DATE FORMAT ERROR!')  # WARNING

        else:
            tei_logger.log('WARNING', f'{url}: ARTICLE INFO NOT FOUND!')  # WARNING

    else:
        # format 2
        article_head_format_2 = bs.find('header', {'id': 'article-head'})
        if article_head_format_2 is not None:
            # format 2 title
            title_tag = article_head_format_2.find('h1')
            if title_tag is not None:
                title = title_tag.get_text(strip=True)
                if len(title) > 0:
                    data['sch:name'] = title
            else:
                tei_logger.log('WARNING', f'{url}: TITLE NOT FOUND IN URL!')
            # format 2 date published and author
            d_and_a_tag = article_head_format_2.find('div', {'class': 'address top'})
            if d_and_a_tag is not None:
                author_tag = d_and_a_tag.find('span', {'class': 'article-author'})
                if author_tag is not None:
                    author = author_tag.get_text(strip=True)
                    if len(author) > 0:
                        data['sch:authors'] = [author]  # INSERT sch:source OPTIONS
                date_pub_tag = d_and_a_tag.find('span', {'id': 'article-date', 'pubdate': 'pubdate', 'datetime': True})
                if date_pub_tag is not None:
                    pub_date = parse_date(date_pub_tag['datetime'].strip(), '%Y-%m-%dT%H:%M')
                    if pub_date is not None:
                        data['sch:datePublished'] = pub_date
                    else:
                        tei_logger.log('WARNING', f'{url}: FAILED TO PARSE DATE PUBLISHED!')
                else:
                    tei_logger.log('WARNING', f'{url}: DATE PUBLISHED NOT FOUND!')
            else:
                tei_logger.log('WARNING', f'{url}: DATE AND  PUBLISHED NOT FOUND!')
        else:  # if neither format 1 or 2 are recognized
            tei_logger.log('WARNING', f'{url} ARTICLE HEADER NOT FOUND')

    article_body = bs.find('div', class_='col-xl-8')
    if article_body is not None:
        section_tag = article_body.find('a', class_='category-meta')
        if section_tag is not None:
            data['sch:articleSection'] = section_tag.text.strip()
            # print(f'{section_tag.text.strip()}')
        else:
            tei_logger.log('DEBUG', f'{url}: SECTION TAG NOT FOUND!')  # WARNING
        keywords_root = article_body.find('div', class_='article-meta')
        if keywords_root is not None:
            article_tags = [a.text.strip() for a in keywords_root.find_all('a') if a is not None]
            article_tags = article_tags[1:]
            if len(article_tags) > 0:
                data['sch:keywords'] = article_tags
                # print(f'{article_tags}')
        else:
            tei_logger.log('DEBUG', f'{url}: TAGS NOT FOUND!')
    else:
        tei_logger.log('WARNING', f'{url}: ARTICLE BODY NOT FOUND!')
    return data


def excluded_tags_spec(tag):
    return tag


BLOCK_RULES_SPEC = {}
BIGRAM_RULES_SPEC = {}
LINKS_SPEC = {}
DECOMP = []
MEDIA_LIST = []


def decompose_spec(article_dec):
    decompose_listed_subtrees_and_mark_media_descendants(article_dec, DECOMP, MEDIA_LIST)
    return article_dec


BLACKLIST_SPEC = []
LINK_FILTER_SUBSTRINGS_SPEC = re.compile('|'.join(['LINK_FILTER_DUMMY_STRING']))

MULTIPAGE_URL_END = re.compile(r'^\b$')  # Dummy


def next_page_of_article_spec(_):
    return None
