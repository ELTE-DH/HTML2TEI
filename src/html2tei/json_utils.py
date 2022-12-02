#!/usr/bin/env python3
# -*- coding: utf-8, vim: expandtab:ts=4

import json
import re

from bs4 import BeautifulSoup


def default_transform_to_html_fun(url, raw_html, warc_logger):
    _ = url, warc_logger
    return raw_html


def _handle_linebreaks_in_json_string(bs, fragment_bs_tag, json_string):
    for line in json_string.split('\n'):
        line_stripped = line.strip()
        if len(line_stripped) > 0:
            if '<' in line_stripped:
                inner_html = BeautifulSoup(line_stripped, 'html.parser')
                fragment_bs_tag.append(inner_html)
            else:
                paragraph = bs.new_tag('p')
                paragraph.string = nonbreaking_replacer(line_stripped)
                fragment_bs_tag.append(paragraph)
    return fragment_bs_tag


def _json_wrapping(url, bs, fragment, logger):
    fragment_as_tag = None
    frag_keys = fragment.keys()
    if 'Txt' in frag_keys or 'imgid' in frag_keys:
        tag_name, tag_attrs, tag_string = None, None, None
        if 'Txt' in frag_keys:
            tag_string = fragment['Txt']
            tag_name = fragment['divtag']
            tag_attrs = {}
        elif 'imgid' in frag_keys:
            tag_attrs = {'href': fragment['imgid']}  # todo: 1292134 > https://nepszava.hu/i/5/3/0/1292134.jpg
            tag_name = 'img'
            tag_string = fragment['sign']+' '+fragment['fotos']+' '+fragment['copy']
        if tag_string is None:
            return None
        fragment_as_tag = bs.new_tag(tag_name, attrs=tag_attrs)
        if '\n' in tag_string.strip():
            _handle_linebreaks_in_json_string(bs, fragment_as_tag, tag_string.strip())
        else:
            if tag_string.startswith('<'):
                inner_html = BeautifulSoup(tag_string, 'html.parser')
                fragment_as_tag.append(inner_html)
            else:
                fragment_as_tag.string = nonbreaking_replacer(tag_string.strip())
    else:
        print('UNKNOWN JSON FRAGMENT', url, fragment)
        logger.log('WARNING', f'{url}: UNKNOWN JSON FRAGMENT')
    return fragment_as_tag


def _json_block_wrapping(url, bs, block_list):
    divkeys = set()  # TODO is there duplication which we have to uniq?
    for tag_as_dict in block_list:
        if 'divclass' in tag_as_dict.keys():
            divkeys.add(tag_as_dict['divclass'])
        else:
            divkeys.add('_'.join(sorted(tag_as_dict.keys())))
    divkeys = list(divkeys)
    if len(divkeys) == 1:
        block_div = bs.new_tag('div', attrs={'class': divkeys[0]})
        return block_div   # TODO else None!


def nonbreaking_replacer(text):
    # https://nepszava.hu/json/cikk.json?id=3094323_a-liverpool-hetet-a-manchester-united-hatot-kapott
    # 1a06bd99-2770-5ee3-a2bb-d05022d4231c.xml 2020-10-05
    text = re.sub(r'(&nbsp;)+', '\N{NO-BREAK SPACE}', text)
    return text


def json_to_html(a_url, json_str, w_logger):
    json_data = json.loads(json_str)
    init_bs = BeautifulSoup('<html><head/><body></body></html>', 'lxml')
    whole = init_bs.new_tag('json_article')
    json_meta_part = dict((key, value) for key, value in json_data.items() if key != 'content')
    json_str = json.dumps(json_meta_part)
    whole.string = nonbreaking_replacer(json_str)
    init_bs.head.append(whole)
    article_root = init_bs.new_tag('article_body_root')
    if 'lead' in json_data.keys():
        lead = json_data['lead']
        if lead is not False:
            lead_tag = init_bs.new_tag('lead')
            lead_tag.string = nonbreaking_replacer(lead)
            article_root.append(lead_tag)
    if 'lead_img' in json_data.keys():
        leadimg = json_data['lead_img']
        lead_tag = init_bs.new_tag('img', attrs={'href': leadimg})
        article_root.append(lead_tag)
    for mainblock in json_data['content']:  # unit_unpacked:
        if isinstance(mainblock, dict):  # article consits only 1 (text)unit
            html_frag = _json_wrapping(a_url, init_bs, mainblock, w_logger)
            if html_frag is not None:
                article_root.append(html_frag)
        elif isinstance(mainblock, list) and len(mainblock) > 0:
            if len(mainblock) == 1:
                html_frag = _json_wrapping(a_url, init_bs, mainblock[0], w_logger)
                if html_frag is not None:
                    article_root.append(html_frag)
            else:
                block_div = _json_block_wrapping(a_url, init_bs, mainblock)
                for oneblock in mainblock:  # dict-ek listája  (ha egyelemű akkor az a képek ?)
                    if isinstance(oneblock, dict):
                        html_frag = _json_wrapping(a_url, init_bs, oneblock, w_logger)
                        if html_frag is not None:
                            block_div.append(html_frag)  # TODO what if block_div is None because json_block_wrapping()?
                article_root.append(block_div)
    init_bs.body.append(article_root)
    return str(init_bs)
