#!/usr/bin/env python3
# -*- coding: utf-8, vim: expandtab:ts=4 -*-

# For the configs
from src.html2tei.tei_utils import decompose_listed_subtrees_and_mark_media_descendants, tei_defaultdict

# For the main Pyhton API
from html2tei.portal_article_cleaner import init_portal as portal_article_cleaner_init_portal

# For the low level API: defining custom modes
from src.html2tei.tei_utils import create_new_tag_with_string, immediate_text, to_friendly
