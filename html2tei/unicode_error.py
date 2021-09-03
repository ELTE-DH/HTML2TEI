# !/usr/bin/env python3
# -*- coding: utf-8, vim: expandtab:ts=4 -*-

import re

from bs4 import BeautifulSoup, NavigableString

from html2tei.tei_utils import unwrap_all, create_new_tag_with_string


def unicode_test(article_text, unicode_strings=re.compile(r'[uU][0-9]([0-9]{3}|[0-9][a-f])')):
    """This tests whether the text of the article contains escaped unicode characters,
        based on the number of typical substrings
    """
    m_count = sum(int(unicode_strings.search(s) is not None) for s in article_text.split())
    return m_count


def article_encoding_correction(article, decompose_fun):
    """Finds useful text in a mixture of json snippets and incorrectly encoded text.
       It also tries to repair damaged (ill-formed HTML) articles
    """
    decompose_fun(article, 'media_unwrap')
    soup = BeautifulSoup('a', 'lxml')
    unwrap_all(article, True)
    ret = extract_first_instance_of_article_text(article)
    article = create_new_tag_with_string(soup, ret, 'root')
    return article


def fix_garbage_unicode_escapes(text_tag):
    """Helper function for quick_encoding_fix
        1. Fix double escaped backslashes
        2. Fix quotations
        3. Add missing backslashes to Unicode escape strings
        4. Fix double Unicode escaping
       This problem appeared in the articles of the magyarnemzet.hu
       JSON snippets in the text: \\&#8221;,\\&#8221;aktiv\\&#8221;:1}}}  ”,„aktiv”:1}}}</p>  ”,„aktiv”:„1”}}}
    """
    if 'u0' in text_tag:
        encoded_article_text = text_tag.replace('\\\\', '\\').replace('”', '"').replace('u0', '\\u0'). \
            replace('\\\\u0', '\\u0').encode('UTF-8').decode('unicode-escape')
        return encoded_article_text
    return text_tag


def extract_first_instance_of_article_text(article_body):
    """The text of the article present multiple times in a garbage HTML.
       This function determines the end of the first instance to ignore the rest.
       This problem appeared in the articles of the magyarnemzet.hu
       Helper for article_encoding_correction
    """
    ret_tags = [fix_garbage_unicode_escapes(cont.strip()) for cont in article_body.contents
                if isinstance(cont, NavigableString) and len(cont.strip()) > 0]
    ret_text = ' '.join(ret_tags)
    encoded_article_text = ret_text.replace('aktiv":1}}}', 'STOP').replace('\\&#8221;aktiv\\&#8221;:1}}}', 'STOP').\
        replace('","aktiv":"1"}}}', 'STOP')
    encoded_article_text = encoded_article_text[:encoded_article_text.find('STOP')]
    return encoded_article_text
