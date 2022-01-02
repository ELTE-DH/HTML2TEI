#!/usr/bin/env python3
# -*- coding: utf-8, vim: expandtab:ts=4 -*-

from bs4 import BeautifulSoup
from justext import get_stoplist, justext

from html2tei.tei_utils import tei_defaultdict, create_new_tag_with_string

stoplist = get_stoplist('Hungarian')


def process_article(one_page_of_article_things, body_log, get_meta_fun, spec_body_params):
    """Using the JusText boilerplate removal tool to extract the article's paragraphs
        Returns the metadata dictionary and paragraphs"""
    url, warc_response_datetime, warc_id, html = one_page_of_article_things
    _ = url, get_meta_fun, spec_body_params  # Silence IDE
    justasoup = BeautifulSoup(features='lxml')
    paragraphs = justext(html, stoplist)
    metas_in_dict = tei_defaultdict()
    metas_in_dict['sch:url'] = url
    justext_paragraphs = [create_new_tag_with_string(justasoup, paragraph.text, 'p') for paragraph in paragraphs
                          if not paragraph.is_boilerplate]
    if len(justext_paragraphs) == 0:  # Justext did not find any relevant (not boilerplate) text in the article
        body_log.log('WARNING', f'JusText did not find any relevant (not boilerplate) text in the article: {url}')
        justext_paragraphs = [create_new_tag_with_string(justasoup, '', 'p')]
    return metas_in_dict, justext_paragraphs
