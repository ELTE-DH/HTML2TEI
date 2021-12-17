#!/usr/bin/env python3
# -*- coding: utf-8, vim: expandtab:ts=4 -*-

from bs4 import BeautifulSoup
from newspaper import Article

from html2tei.tei_utils import tei_defaultdict, create_new_tag_with_string


def process_article(one_page_of_article_things, body_log, get_meta_fun, spec_body_params):
    """Using the Newspaper3k tool to extract the metadata and paragraphs from the article
        Returns the metadata dictionary and paragraphs"""
    _ = body_log, get_meta_fun, spec_body_params  # Silence IDE
    url, warc_response_datetime, warc_id, html = one_page_of_article_things
    n3ksoup = BeautifulSoup(features='lxml')
    metas_in_dict = tei_defaultdict()
    metas_in_dict['sch:url'] = url
    a = Article(url, language='hu')
    a.download(input_html=html)
    a.parse()
    n3k_paragraphs = [create_new_tag_with_string(n3ksoup, p_text, 'p') for p_text in a.text.split('\n')
                      if len(p_text.strip()) > 0]
    if len(n3k_paragraphs) == 0:
        body_log.log('WARNING',
                     f'Newspaper3k did not find any relevant (not boilerplate) text in the article: {url}')
        n3k_paragraphs = [create_new_tag_with_string(n3ksoup, '', 'p')]

    if a.publish_date is not None:
        metas_in_dict['sch:datePublished'] = a.publish_date.replace(tzinfo=None)
    if a.title is not None:
        metas_in_dict['sch:name'] = a.title
    if len(a.authors) > 0:
        metas_in_dict['sch:author'] = a.authors
    if len(a.tags) > 0:
        metas_in_dict['sch:keywords'] = list(a.tags)
    return metas_in_dict, n3k_paragraphs
