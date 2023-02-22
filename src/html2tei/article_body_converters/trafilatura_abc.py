#!/usr/bin/env python3
# -*- coding: utf-8, vim: expandtab:ts=4 -*-

from datetime import datetime

from bs4 import BeautifulSoup
from lxml.etree import tostring
from trafilatura import extract, extract_metadata, bare_extraction

from ..tei_utils import tei_defaultdict, create_new_tag_with_string


def _create_empty_paragraph_list(url, body_log):
    # Logging is required in both use cases of this function
    body_log.log('WARNING', f'trafilatura did not find any relevant text in the article: {url}')
    empty_soup = BeautifulSoup(features='lxml-xml')
    empty_paragraph_list = [create_new_tag_with_string(empty_soup, '', 'p')]
    return empty_paragraph_list


def process_article(one_page_of_article_things, body_log, get_meta_fun, spec_body_params):

    _ = body_log, get_meta_fun, spec_body_params  # Silence IDE
    url, warc_response_datetime, warc_id, raw_html = one_page_of_article_things
    metas_in_dict = tei_defaultdict()
    metas_in_dict['sch:url'] = url

    # metadata and text content is extracted into a dict
    extracted_bare = bare_extraction(raw_html,
                                     target_language="hu",
                                     output_format="xmltei",
                                     favor_precision=True,
                                     include_links=True,
                                     include_images=True,
                                     include_tables=True,
                                     include_formatting=True)

    if 'date' in extracted_bare.keys():
        metas_in_dict['sch:datePublished'] = datetime.strptime(extracted_bare['date'], "%Y-%m-%d")

    if 'author' in extracted_bare.keys():
        print(extracted_bare['author'])
        authors = extracted_bare['author']
        if authors is not None:
            metas_in_dict['sch:author'] = [author.strip() for author in authors.split('; ')]
        else:
            metas_in_dict['sch:author'] = authors

    if 'title' in extracted_bare.keys():
        metas_in_dict['sch:name'] = extracted_bare['title']

    if 'tags' in extracted_bare.keys() and len(extracted_bare['tags']) > 0:
        metas_in_dict['sch:keywords'] = extracted_bare['tags']

    # bare extraction creates 'body' key with tei format etree.Element / has to be parsed as string to create bs4
    body_as_string = tostring(extracted_bare['body'], pretty_print=True, encoding=str)
    soup = BeautifulSoup(body_as_string, 'lxml-xml')

    tei_tag_list = []
    tei_body = soup.find('body')
    if tei_body is not None:
        tei_body.name = 'p'
        tei_body.wrap(soup.new_tag('body'))
        for t in tei_body.find_all():
            t.unwrap()
        """# INVALID CORRECTIONS
        # 1. head h1 or h2
        heads = tei_body.find_all('head')
        if len(heads) > 0:
            for head in heads:
                if head.get_text(strip=True) == extracted_bare['title']:
                    head.decompose()  # HTML2TEI inserts head as title - removed from result to avoid duplication
                elif 'rend' in head.attrs.keys() and head['rend'] == 'h1' or head['rend'] == 'h2':
                    head.name = 'p'
                    head['rend'] = 'head'
                else:
                    print(head.name, head.attrs)

        # 2. cell tag
        # 3. hi tag
        # 4. graphic tag
        # 5. graphic tag attributes
        # 6. ref tag

        tei_tag_list = [tag for tag in tei_body.find_all(recursive=False)]"""


    if len(tei_tag_list) == 0:
        tei_tag_list = _create_empty_paragraph_list(url, body_log)

    return metas_in_dict, tei_tag_list
