#!/usr/bin/env python3
# -*- coding: utf-8, vim: expandtab:ts=4 -*-

from itertools import groupby
from re import compile as re_compile

COLOR = re_compile(r'.*color.*')
LINKS_PATTERNS_TUPLE = ('http', 'www')
LINKS = {'href', 'url', 'data-mce-href', 'src', 'data-src'}
REFERENCE_TAGS = {'a', 'img', '0_MDESC_a', '0_MDESC_img'}
ATTR_TO_DEL = re_compile(r'(highlight|width|height|align|style|sizset|sizcache|size|face)')
ATTR_TO_DEL_TUP = ('highlight', 'width', 'height', 'align', 'style', 'sizset', 'sizcache', 'size', 'face')
TABLE_ATTR_DEL = {'cellpadding', 'cellspacing', 'height', 'width', 'border', 'align', 'style'}
TABLE_TAGS = {'table', '0_MDESC_table', 'td', 'tr', 'th', 'thead', 'tbody', '0_MDESC_td', '0_MDESC_tr', '0_MDESC_th',
              '0_MDESC_thead', '0_MDESC_tbody'}


# Only excluded_tags is used outside of this file


def simplify_alphanumeric_values(tag_attr_value):
    """It simplifies attributes that are irrelevant to the evaluation of labels or unnecessarily unique to the
        human analyst, thus creating more relevant, uniformly manageable groups
       E.g. <div dir=ltr id="35egd5647"> and <div dir=ltr id="654u7">
        to:  <div dir=ltr id=@NUM> and <div id="698994u" dir=ltr>
    """
    a_num_count = sum(c.isdigit() for c in tag_attr_value)
    a_alpha_count = sum(c.isalpha() for c in tag_attr_value)
    if tag_attr_value.isnumeric():
        tag_attr_value = '@NUM'
    elif len(tag_attr_value) > 30:
        # 30 is an approximate value for length  of values that are no longer interpretable or too unique in meaning.
        #  https://magyarnemzet.hu/archivum/sport-archivum/verraszto-evelyn-a-cote-dazuron-hangolt-dohara-4000983/
        #  from: <div data-reactid=\".ja.$&lt;1417106561645=23619524058-250894092@mail=1projektitan=1com&gt;.2:0\">
        #  to: <div data-reactid=@LONG>
        tag_attr_value = '@LONG'
    elif a_num_count > 0 and a_alpha_count > 0:
        # We retain the longest alphanumeric substring of an alphanumeric string
        longest_alphabetic_substring = max((''.join(alpha_chr) for is_alpha, alpha_chr in
                                            groupby(tag_attr_value, key=str.isalpha) if is_alpha), key=len)
        if len(longest_alphabetic_substring) > 4:
            tag_attr_value = f'@{longest_alphabetic_substring}NUM'
            # 4 is an approximate value for a meaningful alphabetic substring
            #  https://magyarnemzet.hu/belfold/bibo-istvan-igazi-demokrata-volt-ezert-nem-felt-6904667/
            #  from: <div id="attachment_6904733" class="wp-caption aligncenter size-full wp-image-6904733
            #  ewebResponsiveImage ewebCol-xs-12 ewebCol-sm-12 ewebCol-md-12 ewebCol-lg-12">
            #  to: <div class=wp-caption @STYLE id=@attachmentNUM style=@STYLE>
        elif a_num_count < 3 and a_alpha_count < 3:
            # A distinction could be made between cases that contain a short alphanumeric code and
            #  those that contain only numbers. Example: <h2 class="p2"> to <h2 class="NUM">
            #  https://abcug.hu/lebontani-mindent-mintha-nem-is-letezett-volna/
            tag_attr_value = '@NUM'
        else:  # Too long, incomprehensible values. E.g.: id="shh457645gtswjf957egfm59erghdj67859frhjfh"
            tag_attr_value = '@NUM'
    return tag_attr_value


def simplify_style_like_attributes(curr_attr, value_ind, value):
    """Helper function for excluded_tags. Run simplify_alphanumeric_values if attr is kept"""
    if any(elem in value for elem in ATTR_TO_DEL_TUP):
        curr_attr[value_ind] = '@STYLE'
    else:  # predominantly numeric values
        curr_attr[value_ind] = simplify_alphanumeric_values(value)


def simplified_tags_spec(tag):
    """This function is used in all places outside of this file where the dictionary shape of the tags is required"""
    tag_attrs = tag.attrs
    if tag.name in REFERENCE_TAGS and (tag.has_attr('title') or tag.has_attr('alt') or tag.has_attr('data-title')):
        if 'title' in tag_attrs.keys():
            tag_attrs['title'] = '@title'
        if 'data-title' in tag_attrs.keys():
            tag_attrs['data-title'] = '@title'
        if 'alt' in tag_attrs.keys():
            tag_attrs['alt'] = '@alt'

    for attr_key in tag_attrs.keys():
        # Simple attribute value
        attr_val = str(tag_attrs[attr_key])
        if any(elem in attr_key for elem in ATTR_TO_DEL_TUP):
            tag_attrs[attr_key] = '@STYLE'
        elif any(elem in attr_val for elem in LINKS_PATTERNS_TUPLE) or attr_key in LINKS:
            tag_attrs[attr_key] = '@LINK'
        elif COLOR.match(attr_key):
            tag_attrs[attr_key] = ''
        elif attr_key == 'target':
            tag_attrs[attr_key] = '@target'

        if isinstance(tag_attrs[attr_key], str) and not tag_attrs[attr_key].startswith('@'):
            # Styles
            if any(elem in attr_key for elem in ATTR_TO_DEL_TUP):
                tag_attrs[attr_key] = '@STYLE'
            simplify_style_like_attributes(tag_attrs, attr_key, tag_attrs[attr_key])
        elif isinstance(tag_attrs[attr_key], list):  # Multi-valued (list type) attributes
            for value_ind, value in enumerate(tag_attrs[attr_key]):
                simplify_style_like_attributes(tag_attrs[attr_key], value_ind, value)
    if tag.name in TABLE_TAGS:
        table_attrs = {attr_key: tag.attrs[attr_key] for attr_key in tag.attrs.keys() if attr_key not in TABLE_ATTR_DEL}
        tag.attrs = table_attrs
    return tag
