#!/usr/bin/env python3
# -*- coding: utf-8, vim: expandtab:ts=4 -*-

from yaml import dump as yaml_dump
from collections import defaultdict
from os.path import join as os_path_join
from json import dumps as json_dumps, loads as json_loads

from html2tei.tei_utils import to_friendly
from html2tei.processing_utils import run_single_process, dummy_fun, process_article


def collect_tags_recursively(out_dict, article_url, tag, excluded_tags_fun):
    """Read the articles to summarize all the structures that occur in the portal schema.
       Finally the accumulated information represents the tree structure as a nested YAML dictionary.
       This is a recursive function!
    """
    _ = article_url  # Silence IDE
    tags = tag.find_all(recursive=False)
    for ch in tags:
        collect_tags_recursively(out_dict[to_friendly(ch, excluded_tags_fun)],  article_url, ch, excluded_tags_fun)


def final_tree(dates, out_files, root_dict, tei_logger):
    """Produce the final form of the aggregated information after a WARC has been processed
        into a nested YAML dictionary"""
    _ = dates, tei_logger  # Silence IDE
    output = json_loads(json_dumps(root_dict))  # Convert to normal dict
    yaml_dump(output, out_files[0], default_flow_style=False)


def nested_dict():
    return defaultdict(nested_dict)  # Recursive definition!


def init_portal(log_dir, output_dir, run_params, portal_name, tei_logger, warc_level_params, rest_config_params):
    """Init variables for processing a portal: HTML Content Tree (This is the only public function of this file)"""
    _ = log_dir, run_params, warc_level_params  # Silence IDE

    article_root_params, decompose_spec, excluded_tags_spec = rest_config_params[1:4]

    # The internal structure of the accumulator is defined in nested_dict function
    accumulator = nested_dict()
    # No files and after processing needed for each article
    after_article_fun, after_article_params, log_file_names_and_modes = dummy_fun, (), ()
    # Filenames for the final function
    final_filenames_and_modes = ((os_path_join(output_dir, f'{portal_name}_tree.txt'), 'w'),)
    # Run this function after all articles are processed
    final_fun = final_tree
    # Process articles one by one with this function
    process_article_fun = process_article
    # From the loaded portal-specific configuration
    #  - TEI logger for logging
    #  - article root params for find_all
    #  - portal-specific decompose functions
    #  - portal-specific simplification rules for the different parts of the attributes,
    #     with merging the irrelevant variations of values
    # Task specific params:
    #  - (sub)function to run after cleaning the article up (decompose unnecessary parts)
    #  - the parameters for the subfunction (accumulator)
    process_article_params = (tei_logger, article_root_params, decompose_spec, excluded_tags_spec,
                              collect_tags_recursively, (accumulator,))
    # Runner function (some task can be run only in single-process mode)
    run_fun = run_single_process

    return accumulator, after_article_fun, after_article_params, log_file_names_and_modes, final_filenames_and_modes, \
        final_fun, process_article_fun, process_article_params, run_fun
