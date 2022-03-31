#!/usr/bin/env python3
# -*- coding: utf-8, vim: expandtab:ts=4 -*

import re

from html2tei import parse_date, decompose_listed_subtrees_and_mark_media_descendants, tei_defaultdict

PORTAL_URL_PREFIX = 'https://www.origo.hu/'

ARTICLE_ROOT_PARAMS_SPEC = [(('div',), {'class': 'o-section-main'})]

SUBJ_DICT = {'auto': 'Autó',
             'filmklub': 'Filmklub',
             'gazdasag': 'Gazdaság',
             'itthon': 'Itthon',
             'nagyvilag': 'Nagyvilág',
             'sport': 'Sport',
             'tafelspicc': 'Tafelspicc',
             'techbazis': 'Techbázis',
             'tudomany': 'Tudomány'
             }


def get_meta_from_articles_spec(tei_logger, url, bs):
    data = tei_defaultdict()
    data['sch:url'] = url

    article_head_format_1 = bs.find('header', class_='article-head')
    if article_head_format_1 is not None: # format 1
        # format 1 title
        title = article_head_format_1.find('h1', class_='article-title')

        if title is not None:
            data['sch:name'] = title.text.strip()
        else:
            tei_logger.log('WARNING', f'{url}: TITLE NOT FOUND IN URL!')
        # format 1 author and date published
        article_info = bs.find('div', class_='article-info')
        if article_info is not None:
            author = article_info.find('span', class_='article-author')
            if author is not None:
                data['sch:author'] = [author.text.strip()]
            else:
                tei_logger.log('WARNING', f'{url}: AUTHOR TAG NOT FOUND!')
            date_tag = article_info.find('div', class_='article-date')
            if date_tag is not None and 'datetime' in date_tag.attrs.keys():
                parsed_date = parse_date(date_tag.attrs['datetime'], '%Y-%m-%dT%H:%M')
                data['sch:datePublished'] = parsed_date
            else:
                tei_logger.log('WARNING', f'{url}: DATE FORMAT ERROR!')

        else:
            tei_logger.log('WARNING', f'{url}: ARTICLE INFO NOT FOUND!')
        # format 1 body contents
        article_body = bs.find('div', class_='col-xl-8')
        if article_body is not None:
            # format 1 article section
            section_tag_f1 = article_body.find('a', class_='category-meta')
            if section_tag_f1 is not None:
                section = section_tag_f1.get_text(strip=True)
                if len(section) > 0:
                    data['sch:articleSection'] = section
            else:
                tei_logger.log('DEBUG', f'{url}: SECTION TAG NOT FOUND!')  # WARNING
            # format 1 keywords
            keywords_root = article_body.find('div', class_='article-meta')
            if keywords_root is not None:
                article_tags = [a.text.strip() for a in keywords_root.find_all('a') if a is not None]
                article_tags = article_tags[1:]
                if len(article_tags) > 0:
                    data['sch:keywords'] = article_tags
                else:
                    tei_logger.log('DEBUG', f'{url}: KEYWORDS NOT FOUND!')

    else:  # format 2
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
                    else:
                        tei_logger.log('WARNING', f'{url}: AUTHOR STRING NOT PRESENT IN TAG!')
                date_pub_tag = d_and_a_tag.find('span', {'id': 'article-date', 'pubdate': 'pubdate', 'datetime': True})
                if date_pub_tag is not None:
                    pub_date = parse_date(date_pub_tag['datetime'].strip(), '%Y-%m-%dT%H:%M')
                    if pub_date is not None:
                        data['sch:datePublished'] = pub_date
                    else:
                        tei_logger.log('WARNING', f'{url}: FAILED TO PARSE DATE PUBLISHED!')
                else:
                    tei_logger.log('WARNING', f'{url}: DATE AUTHOR NOT FOUND!')
            # format 2 article section
            header_tag = bs.find('div', {'class': 'container header-container'})
            if header_tag is not None:
                section_tag = header_tag.find('a', {'class': 'os-tag'})
                if section_tag is not None:
                    section = section_tag.get_text(strip=True)
                    if len(section) > 0:
                        data['sch:articleSection'] = section
                    else:
                        tei_logger.log('WARNING', f'{url}: SECTION NOT FOUND!')
            else:
                tei_logger.log('WARNING', f'{url}: DATE AND AUTHOR NOT FOUND!')

        else:  # format 3 gallery
            gallery_base = bs.find('body', {'class': 'gallery'})
            if gallery_base is not None:

                g_header = gallery_base.find('header')
                if g_header is not None:
                    title_tag = g_header.find('h1', {'class': 'gallery-title'})
                    if title_tag is not None:
                        title = title_tag.get_text(strip=True)
                        if len(title) > 0:
                            data['sch:name'] = title
                        else:
                            tei_logger.log('WARNING', f'{url}: GALLERY ARTICLE TITLE NOT FOUND!')

                # format 3 publish date
                pub_date_tag = bs.find('meta', {'name': 'publish-date', 'content': True})
                if pub_date_tag is not None:
                    pub_date = parse_date(pub_date_tag['content'], '%Y-%m-%d')
                    if pub_date is not None:
                        data['sch:datePublished'] = pub_date
                    else:
                        tei_logger.log('WARNING', f'{url} FAILED TO PARSE PUBDATE OF GALLERY ARTICLE')
                split_url = url.split('/')
                # There are no keywords in gallery articles - 'gallery' is added to keywords
                if split_url[4] == 'galeria':
                    data['sch:keywords'] = ['galéria']
                elif split_url[4] == 'olimpia' and split_url[5] == 'galeria':
                    data['sch:keywords'] = ['olimpia', 'galéria']
                elif split_url[5] == 'galeria':
                    data['sch:keywords'] = ['galéria']
                else:
                    tei_logger.log('WARNING', f'{url} GALLERY LINK FAILED TO PARSE')
                # format 3 article section is only available from link
                if split_url[3] in SUBJ_DICT.keys():
                    data['sch:articleSection'] = SUBJ_DICT[split_url[3]]
                else:
                    tei_logger.log('WARNING', f'{url} GALLERY ARTICLE SECTION UNACCOUNTED FOR')
                # author never present on gallery article

            else:  # format 4 közvetítés
                sports_feed_header = bs.find('div', class_='sportonline_header')
                if sports_feed_header is not None:
                    # TODO write sports feed format
                    title_tag = bs.find('title')
                    if title_tag is not None:
                        title = title_tag.get_text(strip=True)
                        if len(title) > 0:
                            data['sch:name'] = title
                    # format 4 publish date
                    pub_date_tag = bs.find('meta', {'name': 'publish-date', 'content': True})
                    if pub_date_tag is not None:
                        pub_date = parse_date(pub_date_tag['content'], '%Y-%m-%d')
                        if pub_date is not None:
                            data['sch:datePublished'] = pub_date
                        else:
                            tei_logger.log('WARNING', f'{url} FAILED TO PARSE PUBDATE OF GALLERY ARTICLE')

                    # format 4 article section
                    split_url = url.split('/')
                    if split_url[3] in SUBJ_DICT.keys():
                        data['sch:articleSection'] = SUBJ_DICT[split_url[3]]
                    else:
                        tei_logger.log('WARNING', f'{url} GALLERY ARTICLE SECTION UNACCOUNTED FOR')

                    # format 4 keywords taken from url
                    if split_url[4] == 'kozvetites':
                        data['sch:keywords'] = ['közvetítés']
                    elif split_url[4] == 'olimpia' and split_url[5] == 'kozvetites':
                        data['sch:keywords'] = ['olimpia', 'közvetítés']
                    elif split_url[4] == 'focieb' and split_url[5] == 'kozvetites':
                        data['sch:keywords'] = ['focieb', 'közvetítés']


                else:  # if neither format 1 or 2 or 3 are recognized
                    tei_logger.log('WARNING', f'{url} ARTICLE FORMAT UNACCOUNTED FOR')

    # DATE MODIFIED from META TAG - same in all <meta name="modified-date" content="2022-03-17" />
    date_modified_tag = bs.find('meta', {'name': 'modified-date', 'content': True})
    if date_modified_tag is not None:
        date_modified = parse_date(date_modified_tag['content'], '%Y-%m-%d')
        if date_modified is not None:
            data['sch:dateModified'] = date_modified
        else:
            tei_logger.log('WARNING', f'{url} DATE MODIFIED FAILED TO PARSE')

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
