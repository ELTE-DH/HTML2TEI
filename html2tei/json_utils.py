#!/usr/bin/env python3
# -*- coding: utf-8, vim: expandtab:ts=4
import json
from bs4 import BeautifulSoup


def handling_linebreaks_in_json_string(bs, fragment_bs_tag, json_string):
    for line in json_string.split('\n'):
        if len(line.strip()) > 0:
            paragraph = bs.new_tag('p')
            paragraph.string = line.strip()
            fragment_bs_tag.append(paragraph)
    return fragment_bs_tag


def json_wrapping(url, bs, fragment):
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
            handling_linebreaks_in_json_string(bs, fragment_as_tag, tag_string.strip())
        else:
            fragment_as_tag.string = tag_string.strip()
    else:
        print('UNKNOWN JSON FRAGMENT', url, fragment)
    return fragment_as_tag


def json_block_wrapping(url, bs, block_list):
    divkeys = set()
    for tag_as_dict in block_list:
        if 'divclass' in tag_as_dict.keys():
            divkeys.add(tag_as_dict['divclass'])
        else:
            divkeys.add('_'.join(sorted(tag_as_dict.keys())))
    divkeys = list(divkeys)
    if len(divkeys) == 1:
        block_div = bs.new_tag('div', attrs={'class': divkeys[0]})
        return block_div


def json_to_html(a_url, json_str):
    data = json.loads(json_str)
    init_bs = BeautifulSoup('<article_body_root>', 'lxml')  # tag.wrap(bs.new_tag(root_tag.name))
    article_root = init_bs.find('article_body_root')
    if 'lead' in data.keys():
        lead = data['lead']
        if lead is not False:
            lead_tag = init_bs.new_tag('lead')
            lead_tag.string = lead
            article_root.append(lead_tag)
    if 'lead_img' in data.keys():
        leadimg = data['lead_img']
        lead_tag = init_bs.new_tag('img', attrs={'href': leadimg})
        article_root.append(lead_tag)
    for mainblock in data['content']:  # unit_unpacked:
        if isinstance(mainblock, dict):  # article consits only 1 (text)unit
            html_frag = json_wrapping(a_url, init_bs, mainblock)
            if html_frag is not None:
                article_root.append(html_frag)
        elif isinstance(mainblock, list) and len(mainblock) > 0:
            if len(mainblock) == 1:
                html_frag = json_wrapping(a_url, init_bs, mainblock[0])
                if html_frag is not None:
                    article_root.append(html_frag)
            else:
                block_div = json_block_wrapping(a_url, init_bs, mainblock)
                for oneblock in mainblock:  # dict-ek listája  (ha egyelemű akkor az a képek ?)
                    if isinstance(oneblock, dict):
                        html_frag = json_wrapping(a_url, init_bs, oneblock)
                        if html_frag is not None:
                            block_div.append(html_frag)
                article_root.append(block_div)
    return init_bs

