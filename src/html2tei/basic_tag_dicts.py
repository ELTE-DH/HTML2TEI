#!/usr/bin/env python3
# -*- coding: utf-8, vim: expandtab:ts=4 -*-

# eltedh_abc.py + tei_utils.py
INLINE_TAGS = {'felkover', 'dolt', 'kiemelt', 'hivatkozas', 'alahuzott', 'athuzott', 'felsoindex', 'alsoindex',
               'inline_idezet', 'hi', 'ref'}
# eltedh_abc.py
HI_TAGS = INLINE_TAGS.difference({'media_hivatkozas', 'hivatkozas'})

# eltedh_abc.py
PARAGRAPH_LIKE_TAGS = {'bekezdes', 'cimsor', 'forras', 'kerdes',
                       'kozvetites_meta', 'kozvetites_ido', 'kozvetites_szerzo',
                       'komment_meta', 'komment_ido', 'komment_szerzo'}

# eltedh_abc.py
BLOCKS = {'doboz', 'vez_bekezdes', 'lista', 'idezet', 'table_text', 'kozvetites', 'galeria', 'kviz', 'komment'}
# eltedh_abc.py
TEMPORARILY_USED_TAGS = {'media_hivatkozas', 'hivatkozas'}
# eltedh_abc.py
USED_NOTEXT_TAGS = {'galeria', 'media_tartalom', 'beagyazott_tartalom', 'abra', 'social_media'}

# eltedh_abc.py
OUR_BUILTIN_TAGS = {'to_decompose', 'to_unwrap', 'bekezdes', 'doboz', 'vez_bekezdes', 'cimsor',
                    'lista', 'listaelem', 'idezet', 'forras',
                    'felkover', 'dolt', 'kiemelt', 'alahuzott', 'athuzott', 'felsoindex', 'alsoindex',
                    'table_text',
                    'social_media',
                    'inline_idezet',
                    'hivatkozas',
                    'oszlop_valid', 'sor_valid', 'oszlop_sor', 'tablazat_cimsor', 'kozvetites',
                    'kozvetites_meta', 'kozvetites_ido', 'kozvetites_szerzo',
                    'komment', 'komment_meta', 'komment_ido', 'komment_szerzo', 'komment_root',
                    'cimsor', 'galeria',
                    'kviz', 'kerdes', 'valaszblokk', 'valasz', 'forum', 'media_tartalom', 'beagyazott_tartalom',
                    'abra', 'hi', 'ref'}

# configs/*
BASIC_LINK_ATTRS = {'a', '0_MDESC_a', 'img', '0_MDESC_img', 'iframe', '0_MDESC_iframe'}

# read_config.py
BLOCK_RULES = {'idezet': {'rename': {'cimsor': 'felkover'},
                          'default': 'bekezdes',
                          'not_valid_inner_blocks': [],
                          'not_valid_as_outer_for': ['idezet', 'doboz', 'kozvetites', 'galeria', 'kviz']},

               'doboz': {'rename': {
                   'oszlop': 'to_unwrap',
                   'sor': 'bekezdes',
                   'oszlop_sor': 'bekezdes'},
                   'default': 'bekezdes',
                   'not_valid_inner_blocks': [],
                   'not_valid_as_outer_for': ['kozvetites', 'vez_bekezdes', 'komment']},
               'lista': {'rename': {},
                         'default': 'listaelem',
                         'not_valid_inner_blocks': ['doboz'],
                         'not_valid_as_outer_for': ['kozvetites', 'vez_bekezdes'],
                         },
               'vez_bekezdes': {'rename': {'cimsor': 'felkover'},
                                'default': 'bekezdes',
                                'not_valid_inner_blocks': ['doboz'],
                                'not_valid_as_outer_for': ['komment']},
               'table_text': {'rename': {'oszlop': 'oszlop_valid', 'sor': 'sor_valid'},
                              'default': 'oszlop_sor',
                              'not_valid_inner_blocks': ['doboz'],
                              'not_valid_as_outer_for': ['komment']},
               'kozvetites': {'rename': {'bekezdes': 'unwrap'},
                              'default': 'bekezdes',
                              'not_valid_inner_blocks': ['doboz'],
                              'not_valid_as_outer_for': []},
               'galeria': {'rename': {},
                           'default': 'bekezdes',
                           'not_valid_inner_blocks': [],
                           'not_valid_as_outer_for': ['doboz', 'table_text', 'lista', 'kozvetites', 'vez_bekezdes'],
                           },
               'kviz': {'rename': {},
                        'default': 'bekezdes',
                        'not_valid_inner_blocks': ['doboz', 'table_text', 'kozvetites', 'vez_bekezdes'],
                        'not_valid_as_outer_for': ['kozvetites', 'vez_bekezdes']},
               'komment': {'rename': {},
                           'default': 'bekezdes',
                           'not_valid_inner_blocks': ['komment'],
                           'not_valid_as_outer_for': []}}

# eltedh_abc.py + tei_utils.py
MEDIA_DICT = {'media_tartalom': ('media_hivatkozas', 'forras', 'bekezdes', 'hivatkozas'),
              'social_media': ('social_header', 'bekezdes', 'hivatkozas'),
              'abra': ('media_hivatkozas',),
              'beagyazott_tartalom': ('bekezdes', 'hivatkozas', 'media_hivatkozas', 'media_tartalom')
              }

# tei_utils.py
XML_CONVERT_DICT = {'bekezdes': 'p',
                    'idezet': 'quote',
                    'inline_idezet': 'quote',
                    'lista': 'list',
                    'listaelem': 'item',
                    'szakasz': 'to_unwrap',
                    'jegyzet': 'note',
                    'sor_valid': 'row',
                    'table_text': 'table',
                    'tablazat_cimsor': 'head',
                    'kiemelt': 'hi',
                    'valasz': 'item'
                    }
# tei_utils.py
TAGNAME_AND_ATTR_TABLE = {'cimsor': ('p', 'head'),
                          'felkover': ('hi', 'bold'),
                          'dolt': ('hi', 'italic'),
                          'alahuzott': ('hi', 'underline'),
                          'athuzott': ('hi', 'strikeout'),
                          'felsoindex': ('hi', 'superscript'),
                          'alsoindex': ('hi', 'subscript'),
                          'forras': ('p', 'ref'),
                          'kozvetites_meta': ('p', 'meta'),
                          'kozvetites_ido': ('p', 'time'),
                          'kozvetites_szerzo': ('p', 'author'),
                          'komment_meta': ('p', 'meta'),
                          'komment_ido': ('p', 'time'),
                          'komment_szerzo': ('p', 'author'),
                          'kerdes': ('p', 'question')}

# eltedh_abc.py + tei_utils.py
FIGURE_REND_ATTRS = {'media_tartalom': 'media_content',
                     'abra': 'diagram',  # illustration
                     'beagyazott_tartalom': 'embedded_content'}
