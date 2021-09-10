# !/usr/bin/env python3
# -*- coding: utf-8, vim: expandtab:ts=4 -*-

from copy import copy
from collections import defaultdict

from bs4 import Tag
from bs4.element import NavigableString, Comment

from html2tei.excluded_tags_collection import simplified_tags_spec
from html2tei.basic_tag_dicts import INLINE_TAGS, MEDIA_DICT, XML_CONVERT_DICT, TAGNAME_AND_ATTR_TABLE, \
    FIGURE_REND_ATTRS


def join_list(inp_list):
    """Helper function used by to_friendly only"""
    if isinstance(inp_list, list):
        inp_list = ' '.join(i for i in inp_list)
    return inp_list


def to_friendly(ch, excluded_tags_fun):
    """This function convert tag name and sorted attributes to string in order to use it later
       (e.g. tag_freezer in the tables)
    """
    ch = excluded_tags_fun(ch)
    ch = simplified_tags_spec(ch)
    attrs = ' ' + ' '.join(k + '=' + join_list(v) for k, v in sorted(ch.attrs.items()))
    if len(attrs) == 1:
        attrs = ''
    if '\n' in attrs:
        attrs = attrs.replace('\n', ' ')
    return f'<{ch.name}{attrs}>'


def immediate_text(tag):
    """This function counts the number of words (non-whitespace text)
        immediately under the parameter tag excluding comments
    """
    immediate_length = sum(len(c.split()) for c in tag.children if not isinstance(c, Comment) and
                           isinstance(c, NavigableString) and not c.isspace())
    return immediate_length


def real_text_length(tag):
    """This function counts non-whitespace characters in text under the parameter tag recursively!"""
    return sum(int(not i.isspace()) for i in tag.text)


def imtext_children_descendants_of_tag(tag):
    """This function return the following information on the parameter tag:
        1. The number of words (non-whitespace text) immediately below the tag
        2. The names of direct children (hence recursive=False)
        3. The names of all descendant tags (hence no parameter to find_all())
    """
    naked_text = immediate_text(tag) > 0
    child_tags = {c.name for c in tag.find_all(recursive=False)}
    descendants_tags = {c.name for c in tag.find_all()}
    return naked_text, child_tags, descendants_tags


def unwrap_all(article, tag_name):
    for tag in article.find_all(tag_name):
        tag.unwrap()


def decompose_all(article, tag_name):
    for tag in article.find_all(tag_name):
        tag.decompose()


def decomposing(article, decompose_params):
    """Going through the list of tags to be deleted, it performs the (bs4) decomposing"""
    for args, kwargs in decompose_params:
        for it in article.find_all(*args, **kwargs):
            it.decompose()


def mark_media_descendants(whole_article, media_params):
    """This function adds a prefix to the names of each tag below the root of the specified media blocks,
        thus separating these occurrences within the media from the more self-contained tags
    """
    for args, kwargs in media_params:
        for it in whole_article.find_all(*args, **kwargs):
            for c in it.find_all():
                if not c.name.startswith('0_MDESC_'):
                    c.name = f'0_MDESC_{c.name}'
    return whole_article


def decompose_listed_subtrees_and_mark_media_descendants(article_dec, decomp, media_list):
    """This function combines marking the lower level of the media blocks and deleting tags to be deleted"""
    decomposing(article_dec, decomp)
    mark_media_descendants(article_dec, media_list)


def tei_defaultdict(mandatory_keys=('sch:url', 'sch:name'), missing_value=None):
    """Create a defaultdict preinitialized with the mandatory Schema.org keys set to default
    :param mandatory_keys: a tuple of the keys to be explicitly present in the resulting defaultdict
    :param missing_value: the default value for missing (and explicitly created) keys
    :return: a defaultdict with default value: missing_value and mandatory_keys as default keys set to missing_value

    Other values that could be mandatory:
      ('sch:ispartOf', 'sch:name', 'sch:alternateName', 'sch:author', 'sch:datePublished', 'sch:dateModified',
       'sch:articleSection', 'sch:keywords', 'sch:inLanguage', 'sch:license'),
    """
    return defaultdict(lambda: missing_value, {k: missing_value for k in mandatory_keys})


def create_new_tag_with_string(beauty_xml, tag_string, tag_name, append_to=None):
    """Helper function to create a new XML tag containing string in it.
        If provided append the newly created tag to a parent tag
    """
    the_new_tag = beauty_xml.new_tag(tag_name)
    the_new_tag.string = tag_string.strip()
    if append_to is not None:
        append_to.append(the_new_tag)  # BS.TAG.append() not list!
    else:
        return the_new_tag


def language_attr_recognition(original_tag):
    """It saves the attribute that contains language code. Filtering is very basic"""
    for k, v in original_tag.attrs.items():
        if ('lang' in k or 'data-lang' in k) and isinstance(v, str) and len(v) < 6 and '-' not in v:
            return v
    return None


def complex_wrapping(bs, root_tag, default_wrapper, article_url, tei_logger):
    """There is no ready-made method in beautifulsoup to add a wrapper to a text or concatenation of texts and tags
        so that it stays in place in the tree.
       By traversing the level below the current root (.children generator can access NavigableStrings and Tags),
        if it finds an appropriate rank label, leave it in place, but if it is text or a label that should be at
         a lower level in the hierarchy, it is concatenates the text and lower-level tags and wraps them in the desired
          default wrapper tag what the current relative root requires.
       For e.g. going through the subtrees of a box/frame, the direct text and tags
        under the root are wrapped in this method to a paragraph tag, which is the default divider
    """
    tei_logger.log('DEBUG', f'complex_wrapping in {article_url}')
    naked_text, child_tags, desc_tags = imtext_children_descendants_of_tag(root_tag)
    if child_tags <= INLINE_TAGS and root_tag.name not in MEDIA_DICT.keys():
        root_tag.wrap(bs.new_tag(root_tag.name))
        root_tag.name = default_wrapper
    elif naked_text or len(INLINE_TAGS & child_tags) > 0 or \
            (child_tags <= INLINE_TAGS and root_tag.name in MEDIA_DICT.keys()):
        root_contents = []
        naked_text_and_inline_tag = ''
        contents_list = copy(root_tag.contents)
        for it, elem in enumerate(contents_list):
            if (isinstance(contents_list[it], NavigableString) and not contents_list[it].isspace() and
                len(contents_list[it].strip()) > 0) or \
                    (isinstance(contents_list[it], Tag) and contents_list[it].name in INLINE_TAGS):
                if isinstance(naked_text_and_inline_tag, Tag):
                    naked_text_and_inline_tag.append(contents_list[it])
                else:
                    naked_text_and_inline_tag = bs.new_tag(default_wrapper)
                    naked_text_and_inline_tag.append(contents_list[it])
            elif isinstance(contents_list[it], Tag):
                if isinstance(naked_text_and_inline_tag, Tag):
                    root_contents.append(naked_text_and_inline_tag)
                root_contents.append(contents_list[it])
                naked_text_and_inline_tag = ''
        if isinstance(naked_text_and_inline_tag, Tag):
            root_contents.append(naked_text_and_inline_tag)
        root_tag.clear()
        root_tag.extend(root_contents)


def normal_tag_to_tei_xml_converter(bs, article):
    """It replaces the temporary label names with valid TEI labels and inserts the extra levels required by the TEI"""
    for tag in article.find_all():
        tag_name = tag.name
        if tag_name in XML_CONVERT_DICT.keys():
            tag.name = XML_CONVERT_DICT[tag_name]
        elif tag_name in TAGNAME_AND_ATTR_TABLE:
            tag.name = TAGNAME_AND_ATTR_TABLE[tag_name][0]
            tag.attrs = {'rend': TAGNAME_AND_ATTR_TABLE[tag_name][1]}
        elif tag_name == 'vez_bekezdes':
            tag.wrap(bs.new_tag('floatingText', type='lead'))
            tag.name = 'body'
        elif tag_name == 'doboz':
            f = article.find('media_tartalom', recursive=False)
            if f is not None:
                f.wrap(bs.new_tag('p'))
            tag.wrap(bs.new_tag('floatingText', type='frame'))
            tag.name = 'body'
        elif tag_name == 'kviz':
            tag.wrap(bs.new_tag('floatingText', type='quiz'))
            tag.name = 'body'
        elif tag_name == 'forum':
            tag.wrap(bs.new_tag('div', type='forum'))
            tag.name = 'body'
        elif tag_name == 'galeria':
            tag.wrap(bs.new_tag('floatingText', type='gallery'))
            tag.name = 'body'
            for f in tag.find_all('media_tartalom', recursive=False):
                f.wrap(bs.new_tag('p'))
        elif tag_name == 'kozvetites':
            tag.name = 'div'
            tag.attrs = {'type': 'feed'}
        elif tag_name == 'komment':
            tag.name = 'div'
            tag.attrs = {'type': 'comment'}
        elif tag_name == 'komment_root':
            tag.name = 'div'
            tag.attrs = {'type': 'comments_container'}
        elif tag_name == 'valaszblokk':
            tag.name = 'list'
            tag.attrs = {'type': 'quiz'}
        elif tag_name == 'social_media':
            flo_root = bs.new_tag('floatingText')
            flo_root.attrs = {'type': 'social_media_content'}
            convert_link_to_facs_and_make_notes(bs, flo_root, tag)
            tag_attrs = tag.attrs
            flo_root.attrs.update(tag_attrs)
            tag.wrap(flo_root)
            tag.name = 'body'
            tag.attrs = {}
            if not tag.find_all():
                required_empty_p = bs.new_tag('p')
                tag.append(required_empty_p)
        elif tag_name in FIGURE_REND_ATTRS:
            rend = FIGURE_REND_ATTRS[tag_name]
            tag.name = 'figure'
            tag.attrs['rend'] = rend
            convert_link_to_facs_and_make_notes(bs, tag, tag)
        elif tag_name == 'oszlop_sor':
            tag.wrap(bs.new_tag('row'))
            tag.name = 'cell'
        elif tag_name == 'oszlop_valid':
            tag.name = 'cell'
            for p in tag.find_all('bekezdes', recursive=False):
                p.unwrap()
        elif tag_name == 'hivatkozas':
            tag.name = 'ref'
            if 'original' in tag.attrs.keys():
                if 'target' in tag.attrs.keys():
                    tag.attrs['type'] = 'corrected'
                else:
                    tag.attrs['type'] = 'deleted'
                tag.attrs['resp'] = 'script'
                note = bs.new_tag('note')
                origi_ref = bs.new_tag('ref', type='original')
                origi_ref.string = tag.attrs['original']
                note.append(origi_ref)
                tag.append(note)
                del tag.attrs['original']


def convert_link_to_facs_and_make_notes(bs, flo_root, tag):
    """Helper function to normal_tag_to_tei_xml_converter"""
    if 'target' in tag.attrs.keys():
        flo_root.attrs['facs'] = tag.attrs['target']
        del tag.attrs['target']
    if 'original' in tag.attrs.keys():
        tag.attrs['type'] = 'corrected'
        tag.attrs['resp'] = 'script'

        note = bs.new_tag('note')
        note.string = tag.attrs['original']
        del tag.attrs['original']
        note.attrs['corresp'] = 'facs'
        tag.append(note)
