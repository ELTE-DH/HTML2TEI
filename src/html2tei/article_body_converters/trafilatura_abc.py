#!/usr/bin/env python3
# -*- coding: utf-8, vim: expandtab:ts=4 -*-

from dateutil.parser import parse

from bs4 import BeautifulSoup
from trafilatura import extract

from html2tei.tei_utils import tei_defaultdict, create_new_tag_with_string


def _create_empty_paragraph_list(url, body_log):
    # Logging is required in both use cases of this function
    body_log.log('WARNING', f'trafilatura did not find any relevant text in the article: {url}')
    empty_soup = BeautifulSoup(features='lxml')
    empty_paragraph_list = [create_new_tag_with_string(empty_soup, '', 'p')]
    return empty_paragraph_list


def process_article(one_page_of_article_things, body_log, get_meta_fun, spec_body_params):

    _ = body_log, get_meta_fun, spec_body_params  # Silence IDE
    url, warc_response_datetime, warc_id, raw_html = one_page_of_article_things
    metas_in_dict = tei_defaultdict()
    metas_in_dict['sch:url'] = url

    # Extracted in xml format so paragraphs are automatically tagged as 'p', 'quote', 'list', etc.
    extracted_xml = extract(raw_html, target_language='hu', output_format='xml')
    soup = BeautifulSoup(extracted_xml, 'lxml')

    doc = soup.find('doc')
    if doc is not None:

        if 'date' in doc.attrs.keys():
            # TODO added date parsing. Default is str in both extract, and extract_metadata functions
            #  If date is in uniform format we do not need dateutils to parse it!
            date = parse(doc['date'])
            metas_in_dict['sch:datePublished'] = date

        if 'author' in doc.attrs.keys():
            metas_in_dict['sch:author'] = doc['author']

        if 'title' in doc.attrs.keys():
            metas_in_dict['sch:name'] = doc['title']

        if 'tags' in doc.attrs.keys():
            keywords = doc['tags']
            if len(keywords) > 0:
                metas_in_dict['sch:keywords'] = doc['tags']

    main = soup.find('main')
    if main is not None:
        # TODO Append paragraph without stripping?
        paragraph_list = [paragraph for paragraph in main.find_all() if paragraph.get_text(strip=True) is not None]
        if len(paragraph_list) > 0:  # TODO  ???
            paragraph_list = _create_empty_paragraph_list(url, body_log)
    else:
        paragraph_list = _create_empty_paragraph_list(url, body_log)

    return metas_in_dict, paragraph_list

