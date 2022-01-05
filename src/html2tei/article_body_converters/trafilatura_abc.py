#!/usr/bin/env python3
# -*- coding: utf-8, vim: expandtab:ts=4 -*-
from datetime import datetime

from bs4 import BeautifulSoup
from trafilatura import extract, extract_metadata

from html2tei.tei_utils import tei_defaultdict, create_new_tag_with_string


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

    # metadata is extracted into a dict
    extracted_metadata = extract_metadata(raw_html)

    if 'date' in extracted_metadata.keys():
        metas_in_dict['sch:datePublished'] = datetime.strptime(extracted_metadata['date'], "%Y-%m-%d")

    if 'author' in extracted_metadata.keys():
        metas_in_dict['sch:author'] = extracted_metadata['author']

    if 'title' in extracted_metadata.keys():
        metas_in_dict['sch:name'] = extracted_metadata['title']

    if 'tags' in extracted_metadata.keys() and len(extracted_metadata['tags']) > 0:
        metas_in_dict['sch:keywords'] = extracted_metadata['tags']

    # article is extracted into a ready tei format, from which only the body tags are taken.
    extracted_tei_xml = extract(raw_html, target_language='hu', output_format='xmltei')
    soup = BeautifulSoup(extracted_tei_xml, 'lxml-xml')

    tei_tag_list = []
    tei_text_section = soup.find('text')
    if tei_text_section is not None:
        tei_body = soup.find('body')
        if tei_body is not None:
            tei_tag_list = [tag for tag in tei_body.find_all(recursive=False)]

    if len(tei_tag_list) == 0:
        tei_tag_list = _create_empty_paragraph_list(url, body_log)

    return metas_in_dict, tei_tag_list
