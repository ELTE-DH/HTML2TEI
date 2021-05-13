#!/usr/bin/env python3
# -*- coding: utf-8, vim: expandtab:ts=4 -*-

# For the configs
from html2tei.processing_utils import parse_date
from html2tei.basic_tag_dicts import BASIC_LINK_ATTRS
from html2tei.tei_utils import decompose_listed_subtrees_and_mark_media_descendants, tei_defaultdict

# For the main Pyhton API
from html2tei.processing_utils import run_main
from html2tei.read_config import WRITE_OUT_MODES
from html2tei.update_and_filter_tables import diff_all_tag_table
from html2tei.tag_bigrams_maker import init_portal as tag_bigrams_init_portal
from html2tei.html_content_tree import init_portal as content_tree_init_portal
from html2tei.tag_inventory_maker import init_portal as tag_inventory_init_portal
from html2tei.portal_article_cleaner import init_portal as portal_article_cleaner_init_portal

# For the low level API: defining custom modes
from html2tei.validate_hash_zip import init_output_writer
from html2tei.tei_utils import create_new_tag_with_string, immediate_text, to_friendly
from html2tei.processing_utils import run_single_process, run_multiple_process, dummy_fun, process_article
