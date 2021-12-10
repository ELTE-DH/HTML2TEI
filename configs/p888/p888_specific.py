#!/usr/bin/env python3
# -*- coding: utf-8, vim: expandtab:ts=4 -*

import re
import json

from html2tei import parse_date, BASIC_LINK_ATTRS, decompose_listed_subtrees_and_mark_media_descendants, tei_defaultdict

PORTAL_URL_PREFIX = 'https://888.hu'

ARTICLE_ROOT_PARAMS_SPEC = [(('div',), {'class': 'maincontent8'})]

HTML_BASICS = {'p', 'h3', 'h2', 'h4', 'h5', 'em', 'i', 'b', 'strong', 'mark', 'u', 'sub', 'sup', 'del', 'strike',
               'ul', 'ol', 'li', 'table', 'tr', 'td', 'th', 'quote', 'figure', 'iframe', 'script', 'noscript'}

# These are the evident sourcenames used as authors in the 888hu-articles_new.warc.gz articles
SOURCE = ('MTI', ' MTI', 'Mti', 'mti', 'ATV', 'Magyar Nemzet', 'V4NA', 'Origo', 'origo.hu', 'Mandiner', 'mandiner.hu',
          'Operatív Törzs', 'vg.hu', 'Alapjogokért Központ', 'hirado.hu', 'Híradó.hu', 'Hír Tv', 'HírTV',
          'Magyar Hírlap', 'Pesti Srácok', 'MTI-OS', 'Századvég', 'M1', 'Blikk', 'Facebook', 'kultura.hu', 'M4 Sport',
          'VG.hu', 'Newsmax', 'Ripost', 'Nézőpont Intézet', 'pecsujsag.hu', 'Index', 'NNK', 'Metropol', 'Vasárnap.hu',
          'szegedma.hu', 'Magyar Hírlap', 'Migrációkutató Intézet')

# These are not evidently sourcenames, but are treated as such - also in the 888hu-articles_new.warc.gz articles
SOURCE_SECONDARY = ('888.hu.', '888.hu ', '888.hu – V4NA', '888.hu-MTI', 'www.888.hu', '888; MTI', '888 ',
                    '888.hu MN', '888.huu', '888.hu - origo', '888.HU', '888.hu MTI', '888- MTI', ' 888', '888.h ',
                    '888. hu', '888.hu V4NA', '888.hu,MTI', '888.hu ; MTI', '888.hu Origo', '888-MTI', '888.hu (x)',
                    '888', '888.hu')


def get_meta_from_articles_spec(tei_logger, url, bs):
    data = tei_defaultdict()
    data['sch:url'] = url
    article_root = bs.find('div', class_='maincontent8')
    if article_root is not None:
        # DATE: <p>2021.11.29. 13:10</p>
        article_main_content = bs.find('div', class_='main-content')
        if article_main_content is not None:
            date_tag_text = article_main_content.find('p', recursion=False).get_text(strip=True)
            if date_tag_text is not None:
                parsed_date = parse_date(date_tag_text, '%Y.%m.%d. %H:%M')
                if parsed_date is not None:
                    data['sch:datePublished'] = parsed_date
                else:
                    tei_logger.log('DEBUG', f'{url}: DATE FORMAT ERROR!')
            else:
                tei_logger.log('DEBUG', f'{url}: DATE TAG NOT FOUND!')

            # ARTICLESECTION, KEYWORDS, AUTHOR(S), and NAME
            cikkholder_tag = article_main_content.find('div', {'id': 'cikkholder'})
            if cikkholder_tag is not None:

                # ARTICLESECTION
                plugin_holder_tag = cikkholder_tag.find('div', class_='plugin-holder')
                if plugin_holder_tag is not None:
                    article_section_attribute_tag_text = \
                        plugin_holder_tag.find('a', class_='btn-link').get_text(strip=True)
                    if article_section_attribute_tag_text is not None:
                        data['sch:articleSection'] = article_section_attribute_tag_text
                    else:
                        tei_logger.log('DEBUG', f'{url}: SECTION TAG NOT FOUND!')

                # KEYWORDS
                keyword_container_tag = cikkholder_tag.find('div', class_='text')
                if keyword_container_tag is not None:  # there is duplication of 'a' tags without this level
                    keyword_attribute_tags = keyword_container_tag.find_all('a', {'rel': 'tag'})
                    if len(keyword_attribute_tags) > 0:
                        keywords_list = [tag.get_text(strip=True) for tag in keyword_attribute_tags
                                         if tag.get_text(strip=True) is not None]
                        if len(keywords_list) > 0:
                            data['sch:keywords'] = keywords_list
                        else:
                            tei_logger.log('DEBUG', f'{url}: KEYWORD TAGS NOT FOUND!')
                    else:
                        tei_logger.log('DEBUG', f'{url}: KEYWORD CONTAINER TAG EMPTY!')

                # AUTHOR(S)
                note_block_tag = article_main_content.find('div', class_='note-block')
                if note_block_tag is not None:
                    author_or_source = note_block_tag.find('div', class_='text-wrap').get_text(strip=True)
                    if author_or_source is not None:
                        if author_or_source in SOURCE or author_or_source in SOURCE_SECONDARY:
                            data["sch:source"] = [author_or_source]
                        else:
                            # split by: ANY OF THESE ',-–' CHARACTERS FOLLOWED BY WHITESPACE '\s' AND NOT 'a ', 'az ',
                            # 'A ' or 'Az '
                            # TODO regex solution may be over complicated
                            split_list = re.split("[,\-\–]\s(?!a\s|az\s|A\s|Az\s)", author_or_source)
                            if len(split_list) > 0 and split_list[0] != '':
                                source_list, author_list = [], []
                                for author in split_list:
                                    if author in SOURCE or author in SOURCE_SECONDARY:
                                        source_list.append(author.strip())
                                    else:
                                        author_list.append(author.strip())
                                if len(author_list) > 0:
                                    data['sch:author'] = author_list
                                if len(source_list) > 0:
                                    data['sch:source'] = source_list
                    else:
                        tei_logger.log('DEBUG', f'{url}: AUTHOR TAG TEXT EMPTY!')

                # NAME(title):
                article_name_tag_text = cikkholder_tag.find('h1').get_text(strip=True)
                if article_name_tag_text is not None:
                    data['sch:name'] = article_name_tag_text
                else:
                    tei_logger.log('WARNING', f'{url}: TITLE NOT FOUND IN URL!')

            else:
                tei_logger.log('DEBUG', f'{url}: AUTHOR-KEYWORDS-ARTICLESECTION-NAME TAG NOT FOUND!')

        # DATEMODIFIED: <script type='application/ld+json'...
        meta_script_tag_text = bs.find('script', {'type': 'application/ld+json'}).get_text(strip=True)
        if meta_script_tag_text is not None:
            # tag text is written as str of dict - needs converting to dict /w json
            date_modified = json.loads(meta_script_tag_text)["@graph"][-1]["dateModified"]
            if date_modified is not None:
                parsed_modification_date = parse_date(date_modified, '%Y-%m-%dT%H:%M:%S%z')  # only works python 3.6<
                if parsed_modification_date is not None:
                    data['sch:dateModified'] = parsed_modification_date
                else:
                    tei_logger.log('DEBUG', f'{url}: MODIFICAION DATE FORMAT ERROR!')
            else:
                tei_logger.log('DEBUG', f'{url}: MODIFICATION DATE NOT FOUND!')

    else:
        tei_logger.log('WARNING', f'{url}: UNKNOW ARTICLE SCHEMA!')
        return None

    return data


def excluded_tags_spec(tag):
    if tag.name not in HTML_BASICS:
        tag.name = 'else'
    tag.attrs = {}
    return tag


# for more precised tag normalization/generate real tag-inventory or tag-tree use this:
# def excluded_tags_spec(tag):
    # tag_attrs = tag.attrs
    # if tag.name == 'img' and 'data-id' in tag_attrs.keys():
    #    tag_attrs['data-id'] = '@DATA-ID'
    # if tag.name == 'span' and 'data-linkedarticle' in tag_attrs.keys():
    #    tag_attrs['data-linkedarticle'] = '@DATA-LINKEDARTICLE'
    # return tag


BLOCK_RULES_SPEC = {}
BIGRAM_RULES_SPEC = {}
LINKS_SPEC = {}
DECOMP = [(('div',), {'class': 'AdW'})]
MEDIA_LIST = []


def decompose_spec(article_dec):
    decompose_listed_subtrees_and_mark_media_descendants(article_dec, DECOMP, MEDIA_LIST)
    return article_dec


BLACKLIST_SPEC = []
LINK_FILTER_SUBSTRINGS_SPEC = re.compile('|'.join(['LINK_FILTER_DUMMY_STRING']))

MULTIPAGE_URL_END = re.compile(r'^\b$')  # Dummy


def next_page_of_article_spec(_):
    return None
