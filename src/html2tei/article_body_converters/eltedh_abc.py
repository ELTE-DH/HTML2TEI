#!/usr/bin/env python3
# -*- coding: utf-8, vim: expandtab:ts=4 -*

import copy
from bs4 import BeautifulSoup
from bs4.element import NavigableString, Tag, Comment

from html2tei.basic_tag_dicts import *
from html2tei.link_corrector import link_corrector
from html2tei.unicode_error import unicode_test, article_encoding_correction
from html2tei.tei_utils import immediate_text, imtext_children_descendants_of_tag, to_friendly, \
    real_text_length, language_attr_recognition, complex_wrapping, normal_tag_to_tei_xml_converter, unwrap_all, \
    decompose_all

TABLE_CELL = {'oszlop', 'tablazat_cimsor'}

BLOCKS_MINUS_CIMSOR = BLOCKS

MEDIA_MINUS_FIG = {'social_media', 'abra', 'beagyazott_tartalom'}
UNUSED_TAGS = {'unwrap', 'null', 'default'}
TABLES_VALID = {'sor_valid', 'oszlop_sor', 'oszlop_valid'}
PARAGRAPH_AND_INLINES = ({'bekezdes'} | INLINE_TAGS)


# Only process_article is used outside of this file

def process_article(article_page_tups, tei_logger, spec_get_meta_fun, spec_body_params):
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


def correct_and_store_link(tag, link, portal_url_prefix, portal_url_filter, extra_key, article_url):
    """This function stores the result of link_corrector in tag.
       The input links can be:
          - good (no repair required)
          - repairable
          - unrepairable
    """
    link_original = link
    tag.attrs.clear()
    link_new = link_corrector(link, portal_url_prefix, portal_url_filter, extra_key, article_url)
    if link_new is None:
        tag.attrs['original'] = link_original
    elif link_original != link_new:
        tag.attrs['target'] = link_new
        tag.attrs['original'] = link_original
    else:
        tag.attrs['target'] = link_original


def tag_freezer(bs_tag, excluded_tags_fun, link_attrs):
    """This function produces the dictionary form of the current tag.
       It simplifies the different parts of the attributes, with merging the irrelevant variations of values
    """
    if bs_tag.name in link_attrs or language_attr_recognition(bs_tag) is not None:
        # When it has attributes to be preserved, which were marked in the configuration
        f_attrs = copy.deepcopy(bs_tag.attrs)
        tag_exl = to_friendly(bs_tag, excluded_tags_fun)
        bs_tag.attrs = f_attrs
    else:  # No attributes are preserved
        tag_exl = to_friendly(bs_tag, excluded_tags_fun)
        bs_tag.attrs.clear()
    return tag_exl


def disambiguate_table_or_frame(article, article_url, tei_logger):
    """This function disambiguates if selected tags are real tables or just frames/boxes (a typical use in HTML)
        based on the proportion of rows and columns in table tag
    """
    tei_logger.log('DEBUG', f'disambiguate_table_or_frame in {article_url}')
    for tag in article.find_all('table_text'):
        cell, row = 0, 0
        for table_c in tag.find_all():
            if table_c.name in TABLE_CELL:
                cell += 1
            elif table_c.name == 'sor':
                row += 1
            elif table_c.name == 'table_text':
                break
        if cell == row or cell < 2:
            tag.name = 'doboz'


def rename_by_bigram_rules(article, change_by_bigram, article_url, tei_logger):
    """You can specify rules to combine two tag. The combined labels overrides the role of
        the participants or their combined meaning
       a) to_merge: Rename it, if the second member of bigram is the only child of the first member and they contain
        the same text. (this is the most strict condition)
       b) det_by_child: Rename it, if the second member of bigram is the only child of the first member, but it also
        has immediate text (which is not contained by the inner)
       c) det_by_any_child: Rename it, if the second member of bigram is one of its children
       b) det_by_any_desc: Rename it, if the second member of bigram is one of its descendants
        (this is the most permissive condition)
    """
    tei_logger.log('DEBUG', f'rename_by_bigram_rules in {article_url}')
    for tag in reversed(article.find_all(change_by_bigram.keys())):
        # The structures (which could be recursive) can be handled safely from the inside out (hence reversed).
        #  Iterating from the outside to the inside crosses the boundaries of the levels
        naked_text, child_tags, desc_tags = imtext_children_descendants_of_tag(tag)
        # The inner dictionary's key is a tuple of second_tag_part and case
        second_tags_of_bigram = {tup[0] for tup in change_by_bigram[tag.name].keys()}
        if len(desc_tags & second_tags_of_bigram) > 0:
            for second_part_tag, case in change_by_bigram[tag.name].keys():
                parent_level_name, child_level_name = change_by_bigram[tag.name][(second_part_tag, case)]
                if second_part_tag in desc_tags and case == 'det_by_any_desc':
                    # https://www.nnk.gov.hu/index.php/koronavirus-tajekoztato/660-munkasszallok-mukodesere-vonatkozo
                    # -kozegeszsegugyi-jarvanyugyi-szabalyok table tag under attachment has no mean
                    for c in tag.find_all(second_part_tag):
                        c.name = child_level_name
                    tag.name = parent_level_name
                    break
                elif second_part_tag in child_tags and \
                        (case == 'det_by_any_child' or
                         (len(child_tags) == 1 and ((not naked_text and case == 'to_merge')
                                                    or case == 'det_by_child'))):
                    # det_by_child: https://abcug.hu/meg-kellett-nekik-tanitani-hogy-ne-egyenek-meg-mindent-egyszerre
                    # / <p><img> = caption)
                    # det_by_any_child: https://www.nnk.gov.hu/index.php/koronavirus-tajekoztato/442-a-wuhani-uj
                    # -koronavirus-2019-ncov-okozta-jarvany-aktualis-helyzete-az-egeszsegugyi-vilagszervezet-2020
                    # -januar-27-i-helyzetjelentese-alapjan <p><img>... = caption
                    for c in tag.find_all(second_part_tag, recursive=False):
                        c.name = child_level_name
                    tag.name = parent_level_name
                    break


def block_specific_renaming(article, block_dict, article_url, tei_logger):
    """Within special ("block") structures, some members must be given a different name.
       Mainly because of TEI rules
    """
    tei_logger.log('DEBUG', f'block_specific_renaming in {article_url}')
    for block_root in reversed(article.find_all(BLOCKS)):
        # The structures (which could be recursive) can be handled safely from the inside out (hence reversed).
        #  Iterating from the outside to the inside crosses the boundaries of the levels
        block_root_name = block_root.name
        if block_dict[block_root_name]['rename'].keys():
            for descendant_tag in block_root.find_all():
                child_tagname = descendant_tag.name
                if descendant_tag.child_tagname in BLOCKS and descendant_tag.name != 'cimsor':
                    break  # It cannot step inside the root of another block, the rules can change there
                elif child_tagname in block_dict[block_root_name]['rename'].keys():
                    descendant_tag.name = block_dict[block_root_name]['rename'][child_tagname]
    for head in article.find_all('cimsor'):
        for head_desc in head.find_all():
            if head_desc.name not in INLINE_TAGS:
                head_desc.unwrap()


def block_specific_curation_of_internal_structure(article, block_dict, article_url, tei_logger):
    """In HTML, certain tags are often used inconsistently or levels are duplicated.
       This function sorts the structures when the special blocks (lead, report, frame, table, list, gallery, quiz)
        contain each other.
       The specified rules define the hierarchy between block's roots by which the code decides whether the current
        occurrence is valid, or one excludes the interpretation of the other.
       At the same time the rules required by the TEI
    """
    tei_logger.log('DEBUG', f'rename_by_bigram_rules in {article_url}')
    for tag in article.find_all(BLOCKS):
        tag_name = tag.name
        tag_text = tag.text.strip()
        # Block in block
        for tag_descendant in tag.find_all(BLOCKS):
            ch_text = tag_descendant.text.strip()
            if tag_name == tag_descendant.name and tag_text == ch_text:
                # Double root
                tag_descendant.unwrap()
            else:
                # Invalid structure
                block_tag_rules_dict = block_dict[tag_name]
                if tag_descendant.name in block_tag_rules_dict['not_valid_inner_blocks']:
                    # A frame in a table https://www.magyaridok.hu/sport/ez-tortent-az-eb-n-eredmenyek-tabellak-753676/
                    tag_descendant.unwrap()
                elif tag_descendant.name in block_tag_rules_dict['not_valid_as_outer_for']:
                    # A table in a quote: https://www.magyaridok.hu/belfold/185128-185128/ <idezet><table_text>
                    tag.name = 'to_unwrap'


def block_structure(article, bs, block_dict, article_url, tei_logger):
    """Arranges the internal structure of the block for a uniform structure.
       Checks to see if the expected division units are at the level below the root.
       For example, in the case of a list, the list item, in the case of a lead, the paragraphs, or at least
        an equivalent label (not a formatting label or a text without a wrapper).
       The complex wrapper is able to concatenate and package texts and formatting labels
    """
    tei_logger.log('DEBUG', f'block_structure in {article_url}')
    for block_tag in article.find_all(BLOCKS_MINUS_CIMSOR):
        default_child_name = block_dict[block_tag.name]['default']
        complex_wrapping(bs, block_tag, default_child_name, article_url, tei_logger)
    for a_list in article.find_all('lista'):
        for list_root_child in a_list:
            if list_root_child.name != 'listaelem':
                list_root_child.wrap(bs.new_tag('listaelem'))


def correct_table_structure(article, bs, article_url, tei_logger):
    """Corrects tables inherited from HTML that are corrupted or incomplete in structure"""
    tei_logger.log('DEBUG', f'correct_table_structure in {article_url}')
    for tab in article.find_all('table_text'):
        for table_root_direct_child in tab.find_all(recursive=False):
            if table_root_direct_child.name not in TABLES_VALID:  # Non table-member
                table_root_direct_child.unwrap()
        for table_root_direct_child in tab.find_all(recursive=False):
            if table_root_direct_child.name == 'sor_valid' and \
                    len(table_root_direct_child.find_all('oszlop_valid', recursive=False)) == 0:
                # No column in the row, so we make an 1×1 field
                table_root_direct_child.name = 'oszlop_sor'
    for tab in article.find_all('table_text'):
        # No row around columns
        if len(tab.find_all('oszlop_valid', recursive=False)) > 0:
            missing_root_replacement(bs, 'oszlop_valid', False, 'sor_valid', tab)
        unwrap_all(tab, 'bekezdes')
        for row in tab.find_all('sor_valid'):
            if immediate_text(row) > 0:
                complex_wrapping(bs, row, 'oszlop_valid', article_url, tei_logger)
    for row in article.find_all('sor_valid'):
        for main_subtree in row.find_all(recursive=False):
            if main_subtree.name != 'oszlop_valid':
                main_subtree.wrap(bs.new_tag('oszlop_valid'))


def missing_root_replacement(bs, divname, rec, root_name, tab):
    """Replace when a block with a fixed structure (e.g., list, table rows) is missing the root.
        It was not in HTML and this cannot be validated in TEI
    """
    row_root = ''
    one_row = False
    for tag in tab.find_all(recursive=rec):
        if tag.name == divname and tag.parent.name != root_name:
            if not one_row:
                row_root = bs.new_tag(root_name)
                one_row = True
                tag.insert_before(row_root)
            row_root.append(tag.extract())
        elif tag.name != divname:
            row_root = ''
            one_row = False


def deal_with_paragraphs(article, article_url, tei_logger):
    """Paragraphs, and tags equivalent to paragraphs (according to the TEI schema) are often overused in HTML.
       The not_valid_in_p tags in the TEI can be encoded with both <p> with different attributes and therefore cannot
        contain each other.
       In these cases, it must be decided which levels can be omitted for the TEI to be valid
    """
    tei_logger.log('DEBUG', f'deal_with_paragraphs in {article_url}')
    for p_tag in article.find_all('bekezdes'):
        p_naked_text, p_child_tags, p_desc_tags = imtext_children_descendants_of_tag(p_tag)
        if len(p_child_tags & PARAGRAPH_LIKE_TAGS) > 0 or (not p_naked_text and len(p_child_tags & INLINE_TAGS) == 0):
            # If a paragraph contains a label that is not valid within a paragraph and it has a more special meaning
            #  or it has no text of its own and contains a higher-ranking tag, so this paragraph level is unnecessary
            p_tag.unwrap()
        elif not p_naked_text and 'bekezdes' in p_desc_tags and p_desc_tags < PARAGRAPH_AND_INLINES \
                and len(p_tag.find_all('bekezdes')) == 1:
            p_tag.find('bekezdes').name = 'to_unwrap'
    # It can be handled safely with two separate iterations. The second checks the labels equivalent to the paragraphs
    #  for non-valid combinations
    for p_like_tag in article.find_all(PARAGRAPH_LIKE_TAGS):
        plike_naked_text, plike_child_tags, plike_desc_tags = imtext_children_descendants_of_tag(p_like_tag)
        if 'bekezdes' in plike_desc_tags and plike_desc_tags < PARAGRAPH_AND_INLINES \
                and len(p_like_tag.find_all('bekezdes')) == 1:
            p_like_tag.find('bekezdes').name = 'to_unwrap'


def handling_unnecessary_wrappers(article, article_url, tei_logger):
    """This function:
        - Interprets the levels inherited from HTML
        - Finds which level is redundant, or can be omitted for a clear structure free of duplication
    """
    tei_logger.log('DEBUG', f'unnecessary_wrappers in {article_url}')
    for a_tag in article.find_all(name=lambda x: x.name not in BLOCKS):
        naked_text, child_tags, desc_tags = imtext_children_descendants_of_tag(a_tag)
        if len(child_tags) == 1 and a_tag.name in child_tags:
            if not naked_text and len(child_tags) > 0:  # Duplicated level
                a_tag.unwrap()
            elif naked_text and a_tag.name in HI_TAGS:  # Variation of duplicated level
                unwrap_all(article, a_tag.name)
    for i_tag in article.find_all(HI_TAGS):
        i_tagname = i_tag.name
        # Double formatting
        in_naked_text, in_child_tags, in_desc_tags = imtext_children_descendants_of_tag(i_tag)
        if i_tagname in in_desc_tags:
            unwrap_all(article, i_tagname)
    for ref in article.find_all('hivatkozas'):
        unwrap_all(ref, PARAGRAPH_LIKE_TAGS)


def handling_paragraphs_and_formatting_hierarchy(article, bs, article_url, tei_logger):
    """Formatting should be at the lowest level.
       If it is higher than the paragraph, this code restores the hierarchy while preserving the scope of formatting
    """
    # Example: formatting tag ('strong') upper than <p>:
    # https://vs.hu/kozelet/osszes/video-jarokelok-koze-hajtott-az-autos-melbourne-ben-harman-meghaltak-0121
    for i_tag in reversed(article.find_all(HI_TAGS)):
        # The structures (which could be recursive) can be handled safely from the inside out (hence reversed).
        #  Iterating from the outside to the inside crosses the boundaries of the levels
        in_naked_text, in_child_tags, in_desc_tags = imtext_children_descendants_of_tag(i_tag)
        p_like_child = PARAGRAPH_LIKE_TAGS & in_child_tags
        if len(p_like_child) == 1 and in_child_tags.difference(in_desc_tags) <= HI_TAGS:
            p_like_child_name = p_like_child.pop()
            for inlines_child in i_tag.find_all(p_like_child_name, recursive=False):
                inlines_child.wrap(bs.new_tag(p_like_child_name))
                if len(inlines_child.attrs.keys()) > 0:
                    tei_logger.log('DEBUG', f'{article_url}: UNEXPECTED ATTRIBUTE HERE:'
                                            f'{inlines_child.name}{inlines_child.attrs}')
                inlines_child.name = i_tag.name
            if in_naked_text:
                complex_wrapping(bs, i_tag, i_tag.name, article_url, tei_logger)
            i_tag.unwrap()


def handling_media_blocks_attrs_and_tags(article_url, article, tei_logger):
    """1. rootless media_link > evaluation
       2. Automatic elimination of duplicate levels
       3. independent image and gallery automatic recognition, correction
       4. where expected, "transporting" the reference to the root
    """
    for direct_facs in article.children:
        if isinstance(direct_facs, Tag) and direct_facs.name == 'media_hivatkozas':
            direct_facs.name = 'media_tartalom'

    for media in reversed(article.find_all(MEDIA_DICT.keys())):
        # The structures (which could be recursive) can be handled safely from the inside out (hence reversed).
        #  Iterating from the outside to the inside crosses the boundaries of the levels
        media_attr_keys = media.attrs.keys()
        if 'target' in media_attr_keys or media.name == 'social_media':
            for media_inner_tag in media.find_all():
                if media_inner_tag.name == 'media_hivatkozas':
                    media_inner_tag.name = 'hivatkozas'
                elif media_inner_tag.name not in MEDIA_DICT[media.name] and media_inner_tag.name not in INLINE_TAGS:
                    media_inner_tag.unwrap()
        else:
            media_facs_list_new = [facs.attrs for facs in media.find_all('media_hivatkozas', target=True)]
            if len(media_facs_list_new) == 1:
                media.attrs = media_facs_list_new[0]
                media.find('media_hivatkozas').unwrap()
            elif len(media_facs_list_new) > 1:  # convert into gallery
                for facs in media.find_all('media_hivatkozas'):
                    facs.name = 'media_tartalom'
                media.name = 'galeria'

    for caption in article.find_all(FIGURE_REND_ATTRS.keys()):
        if len(caption.attrs) == 0 and caption.find(FIGURE_REND_ATTRS.keys()) is not None:
            caption.unwrap()

    for media in article.find_all(MEDIA_DICT.keys()):
        for media_inner_tag in media.find_all():
            if media_inner_tag.name not in MEDIA_DICT.keys() and media_inner_tag.name not in MEDIA_DICT[media.name] \
                    and media_inner_tag.name not in INLINE_TAGS:
                media_inner_tag.unwrap()
            elif media_inner_tag.name in MEDIA_DICT.keys():
                if len(media.attrs) == 0:
                    media.unwrap()
                else:
                    tei_logger.log('DEBUG', f'{article_url}: MEDIA ELEMENT IN MEDIA ELEMENT')

    for rest_media_reference in article.find_all('media_hivatkozas'):
        rest_media_reference.name = 'media_tartalom'


def isempty_figures_and_galleries(article, article_url, tei_logger):
    """Images and galleries cannot always be downloaded in their entirety, so the code considers which blocks are
        worth preserving. ('clues' that contain neither a caption nor a link can be discarded)
    """
    for fig in article.find_all('media_tartalom'):
        if len(fig.text.strip()) == 0 and len(fig.attrs) == 0:
            fig.decompose()
    for isempty_galeries in article.find_all('galeria'):
        if isempty_galeries.find('media_tartalom') is None:
            if real_text_length(isempty_galeries) > 0:
                tei_logger.log('DEBUG', f'{article_url}: GALLERY WITH CAPTION, BUT WITHOUT ANY FIGURES? '
                                        f'{isempty_galeries}')
            isempty_galeries.name = 'to_decompose'
    decompose_all(article, 'to_decompose')
    for social_figure in article.find_all(MEDIA_MINUS_FIG):
        ref_tags = [c.name for c in social_figure.find_all(lambda tag: tag.has_attr('target'))]
        if real_text_length(social_figure) == 0 and len(ref_tags) == 0 and not social_figure.has_attr('target'):
            tei_logger.log('DEBUG', f'{article_url}: EMPTY SOCIAL MEDIA CONTENT OR FIGURE {social_figure}')
            social_figure.decompose()


def correct_lists(bs, l_article, article_url, tei_logger):
    """This function corrects irregular lists which was inherited from HTML"""
    tei_logger.log('DEBUG', f'correct_lists in {article_url}')
    for li in l_article.find_all('item'):
        if li.parent.name != 'list':
            missing_root_replacement(bs, 'item', True, 'list', l_article)
            break


def prepare_tei_body(art_child_tags, art_naked_text, article, bs, article_url, tei_logger):
    """Going through the first level below the article root, it prepares the main subtrees before
        writing out as TEI XML.
       If it finds direct text or an inline tag by iterating through the direct subtrees of the body, it converts it
        to a paragraph.
       This is a variant of the complex_wrapping() method, but with less copy (it is avoidable at this point
        with using a list of subtrees as output)
    """

    tei_logger.log('DEBUG', f'prepare_tei_body in {article_url}')
    tei_body_contents_list = []
    if art_naked_text or len(INLINE_TAGS & art_child_tags) > 0:
        concatenated_naked_and_freetag = ''
        for c in article.children:
            # This generator can access both text and labels at the same level. (the first from the current node)
            if isinstance(c, NavigableString) and len(c.strip()) > 0:
                text = copy.copy(c)
                if isinstance(concatenated_naked_and_freetag, str):
                    concatenated_naked_and_freetag = bs.new_tag('p')
                concatenated_naked_and_freetag.append(text)
            elif isinstance(c, Tag) and c.name in INLINE_TAGS:
                naked_inline_tag = copy.copy(c)
                if isinstance(concatenated_naked_and_freetag, str):
                    concatenated_naked_and_freetag = bs.new_tag('p')
                concatenated_naked_and_freetag.append(naked_inline_tag)
            elif isinstance(c, Tag):
                if isinstance(concatenated_naked_and_freetag, Tag):
                    tei_body_contents_list.append(concatenated_naked_and_freetag)  # list
                    concatenated_naked_and_freetag = ''
                tei_body_contents_list.append(c)
        if isinstance(concatenated_naked_and_freetag, Tag):
            tei_body_contents_list.append(concatenated_naked_and_freetag)
    else:
        # If no packaging was required for any of the subtrees, the output should still be a list.
        #  At this stage, the texts may contain unnecessary line breaks, and so we throw away them as well
        tei_body_contents_list = [subtree for subtree in article.children if not isinstance(subtree, NavigableString)]
    return tei_body_contents_list


def select_attributes_to_preserve(bs_tag, extra_k, article_url, tei_logger):
    """Select attributes which was marked in the dictionary as attributes to keep"""
    relevant_attrs = {}
    if extra_k != 'default':
        if extra_k in bs_tag.attrs.keys():
            relevant_attrs['target'] = bs_tag.attrs[extra_k]
        else:
            tei_logger.log('WARNING', f'{article_url}: ATTRIBUTE KEY IS NOT IN THE ATTRIBUTES OF THE TAG {bs_tag}, '
                                      f'{extra_k}!')
    else:
        lang = language_attr_recognition(bs_tag)
        if lang is not None:
            relevant_attrs['xml:lang'] = lang
    bs_tag.attrs.clear()
    bs_tag.attrs = relevant_attrs


def real_lead_general_test(bs_article, article_url, tei_logger):
    """Verification: If the lead is not at the beginning of the article, it may indicate that the lead tag is
        being used inconsistently
    """
    for i, lead in enumerate(bs_article.find_all('vez_bekezdes')):
        if bs_article.text.find(lead.text[0:20]) > 5 and i > 0:
            tei_logger.log('DEBUG', f'{article_url} The lead is not at the beginning of the article. {lead.text[0:10]}')
            lead.name = 'bekezdes'


def normal_tag_names_by_dict_new(article, bs, excluded_tags_fun, tag_normal_dict, link_attrs, url_prefix,
                                 portal_url_filter, article_url, tei_logger):
    """This function generates the dictionary form of the tags, retrieves its normalized name from the dictionary,
        and then performs the renaming and other specific operations accordingly
    """
    for tag in article.find_all():
        tag_exl = tag_freezer(tag, excluded_tags_fun, link_attrs)
        if tag_exl in tag_normal_dict.keys():
            # Look up the normalised name for the tag and return it with the attributes to be retained if there are any
            normalized_name, extra_key = tag_normal_dict[tag_exl].split('\t', maxsplit=2)
            if normalized_name in UNUSED_TAGS:
                tag.name = 'to_unwrap'
            elif normalized_name in BLOCKS or normalized_name == 'szakasz':
                tag.name = normalized_name
                tag.attrs.clear()
            elif normalized_name == 'decompose':
                tag.name = 'to_decompose'
            elif ';' in normalized_name:
                inner_level, outer_level = normalized_name.split(';', maxsplit=1)
                tag.wrap(bs.new_tag(outer_level))
                tag.attrs.clear()
                tag.name = inner_level
            else:
                tag.name = normalized_name
                if len(tag.attrs) != 0:
                    select_attributes_to_preserve(tag, extra_key, article_url, tei_logger)
                    if 'target' in tag.attrs.keys():
                        href = tag.attrs['target']
                        correct_and_store_link(tag, href, url_prefix, portal_url_filter, extra_key, article_url)
                        if normalized_name == 'media_hivatkozas' and 'target' not in tag.attrs:
                            tag.name = 'to_unwrap'

            if len(tag.text.strip()) == 0 and tag.name not in TEMPORARILY_USED_TAGS \
                    and tag.name not in MEDIA_DICT.keys() and tag.name not in USED_NOTEXT_TAGS \
                    and tag.name not in link_attrs and tag.name != 'to_decompose':
                tag.name = 'to_unwrap'  # Tags that only currently do not contain text
        else:  # Unrated tags
            tei_logger.log('WARNING', f'{article_url} The tag is not in the dictionary.'
                                      f'The dictionary needs to be updated ({tag.name}, {tag})')
            tag.name = 'to_unwrap'


def article_body_converter(tei_logger, article_url, raw_html, spec_params):
    """This function cleans and converts HTML content into a valid TEI XML"""
    article_roots, decompose_fun, excluded_tags_fun, tag_normal_dict, link_attrs, block_dict, change_by_bigram, \
        portal_url_prefix, portal_url_filter = spec_params
    raw_html = raw_html.replace('<br>', ' ')
    bs = BeautifulSoup(raw_html, 'lxml')
    for args, kwargs in article_roots:
        article = bs.find(*args, **kwargs)
        if article is not None:
            break
    else:
        tei_logger.log('WARNING', f'{article_url} ARTICLE BODY ROOT NOT FOUND!')
        return None

    if unicode_test(article.text) > 25 or article.text.count("00e1") > 10:
        # These two numbers are an approximation to separate normal coded and faulty items.
        article = article_encoding_correction(article, decompose_fun)
        tei_logger.log('WARNING', f'{article_url} BAD ENCODING (ARTICLE BODY)!')
    decompose_fun(article)
    article.name = 'article_body_root'
    for element in article(text=lambda text: isinstance(text, Comment)):
        element.extract()  # Delete the Comments
    # 1) Renaming based on manually evaluated tag table(dictionary)
    normal_tag_names_by_dict_new(article, bs, excluded_tags_fun, tag_normal_dict, link_attrs, portal_url_prefix,
                                 portal_url_filter, article_url, tei_logger)

    for un_tag in article.find_all('szakasz'):
        if immediate_text(un_tag) > 0:
            un_tag.name = 'bekezdes'
        else:
            un_tag.unwrap()

    # Decompose/unwrap
    decompose_all(article, 'to_decompose')
    unwrap_all(article, 'to_unwrap')

    # 2) BIGRAM RULES
    if len(change_by_bigram) > 0:
        rename_by_bigram_rules(article, change_by_bigram, article_url, tei_logger)

    # 3) FILTER: table/frame
    disambiguate_table_or_frame(article, article_url, tei_logger)

    # 4) BLOCK specific RENAMING RULES
    block_specific_renaming(article, block_dict, article_url, tei_logger)

    # Decompose/unwrap
    decompose_all(article, 'to_decompose')
    unwrap_all(article, 'to_unwrap')

    # 5) Media
    handling_media_blocks_attrs_and_tags(article_url, article, tei_logger)

    # 6) Cleaning: Delete tags that do not contain text and are used temporarily
    for tag in article.find_all():
        if len(tag.text.strip()) == 0 and tag.name not in USED_NOTEXT_TAGS and tag.name not in link_attrs:
            tag.unwrap()
        if tag.name not in OUR_BUILTIN_TAGS:
            tag.name = 'to_unwrap'

    real_lead_general_test(article, article_url, tei_logger)

    # 7/a) Detect and delete unnecessary levels
    handling_unnecessary_wrappers(article, article_url, tei_logger)
    unwrap_all(article, 'to_unwrap')

    # 7/b) Detect and delete unnecessary <p>-levels
    deal_with_paragraphs(article, article_url, tei_logger)

    # 8) Inline tags and paragraphs hierarchy
    handling_paragraphs_and_formatting_hierarchy(article, bs, article_url, tei_logger)

    # 9) Checking block's structure
    block_specific_curation_of_internal_structure(article, block_dict, article_url, tei_logger)

    correct_table_structure(article, bs, article_url, tei_logger)

    deal_with_paragraphs(article, article_url, tei_logger)

    block_structure(article, bs, block_dict, article_url, tei_logger)

    unwrap_all(article, 'to_unwrap')

    handling_unnecessary_wrappers(article, article_url, tei_logger)

    isempty_figures_and_galleries(article, article_url, tei_logger)

    # 10) Curating the media block's inner structure
    for media in article.find_all(MEDIA_DICT.keys()):
        """Based on an earlier step, only children tags whose names were validated remained. All other direct text can
        be packaged in a default tag. Copying the contents of the label is necessary precisely because of the difficulty
        of moving (deleted on its own) direct ('naked') texts. (Required because of TEI.)"""
        complex_wrapping(bs, media, 'bekezdes', article_url, tei_logger)

    deal_with_paragraphs(article, article_url, tei_logger)
    unwrap_all(article, 'to_unwrap')
    missing_root_replacement(bs, 'komment', False, 'komment_root', article)

    # 11) Rename to XML tags and insert the extra levels required by XML
    article.name = 'body'
    article.attrs.clear()
    normal_tag_to_tei_xml_converter(bs, article)

    # 12) Checking the structure of the article(<body>) and generating the output of the TEI file printout
    art_naked_text, art_child_tags, art_desc_tags = imtext_children_descendants_of_tag(article)

    # The TEI schema does not tolerates when the direct subtrees of the article body are '<figure>-s', so an extra
    #  <p>-level must be inserted (at least in the case of the first occurrence)
    if 'figure' in art_child_tags and len(art_child_tags) == 1:
        for art_child in article.children:
            if art_child.name == 'figure':
                art_child.wrap(bs.new_tag('p'))
                break

    # Not valid by TEI schema if there is only one figure in the floatingText (an extra 'p' level must be inserted)
    for flo in article.find_all('body'):
        flo_child = flo.find_all(recursive=False)
        if len(flo_child) == 1 and flo_child[0].name == 'figure':
            flo.wrap(bs.new_tag('body'))
            flo.name = 'p'

    # If a headless list was inherited from the html source
    correct_lists(bs, article, article_url, tei_logger)

    if real_text_length(article) == 0 and len(article.find_all()) == 0:
        tei_logger.log('WARNING', f'{article_url}: ARTICLE BODY IS EMPTY!')
        return 'EMPTY ARTICLE'

    tei_body_contents_list = prepare_tei_body(art_child_tags, art_naked_text, article, bs, article_url, tei_logger)

    return tei_body_contents_list
