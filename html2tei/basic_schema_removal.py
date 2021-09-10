#!/usr/bin/env python3
# -*- coding: utf-8, vim: expandtab:ts=4 -*-

from newspaper import Article
from bs4 import BeautifulSoup
from justext import get_stoplist, justext

from html2tei.article_body_converter import article_body_converter
from html2tei.tei_utils import tei_defaultdict, create_new_tag_with_string

STOPLIST = get_stoplist('Hungarian')


def use_justext(one_page_of_article_things, body_log, get_meta_fun, spec_body_params):
    """Using the JusText boilerplate removal tool to extract the article's paragraphs
        Returns the metadata dictionary and paragraphs"""
    url, warc_response_datetime, warc_id, html = one_page_of_article_things
    _ = url, get_meta_fun, spec_body_params  # Silence IDE
    justasoup = BeautifulSoup(features='lxml')
    paragraphs = justext(html, STOPLIST)
    metas_in_dict = tei_defaultdict()
    metas_in_dict['sch:url'] = url
    justext_paragraphs = [create_new_tag_with_string(justasoup, paragraph.text, 'p') for paragraph in paragraphs
                          if not paragraph.is_boilerplate]
    if len(justext_paragraphs) == 0:  # Justext did not find any relevant (not boilerplate) text in the article
        body_log.log('WARNING', f'JusText did not find any relevant (not boilerplate) text in the article: {url}')
        justext_paragraphs = [create_new_tag_with_string(justasoup, '', 'p')]
    return metas_in_dict, justext_paragraphs


def use_newspaper(one_page_of_article_things, body_log, get_meta_fun, spec_body_params):
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
        body_log.log('WARNING', f'Newspaper3k did not find any relevant (not boilerplate) text in the article: {url}')
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


def get_pretty_tei_article(article_page_tups, tei_logger, spec_get_meta_fun, spec_body_params):
    """It executes our own metadata extraction and text extraction, normalization,
        TEI to XML conversion method per URL"""
    (one_url, warc_response_datetime, warc_id, raw_html) = article_page_tups
    bs = BeautifulSoup(raw_html, 'lxml')
    meta = spec_get_meta_fun(tei_logger, one_url, bs)
    if meta is not None:
        converted_body_list = article_body_converter(tei_logger, one_url, raw_html, spec_body_params)
        return meta, converted_body_list
    else:
        return None, None
