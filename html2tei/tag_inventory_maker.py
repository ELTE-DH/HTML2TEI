#!/usr/bin/env python3
# -*- coding: utf-8, vim: expandtab:ts=4 -*-

from collections import defaultdict
from os.path import join as os_path_join
from random import sample as random_sample

from html2tei.tei_utils import immediate_text, to_friendly
from html2tei.processing_utils import run_single_process, dummy_fun, process_article


def summarize_children_or_subtree(tag_dict, recursive, article_url, article_body_root, excluded_tags_fun):
    """This function summarizes the properties of each occurrence of the tags (direct or all descendants):
        - the frequency for each tag
        - the (average) word count of all the texts it contains
        - the (average) number of descendant tags
        - the URLs of (some random) occurrences
        - the (average) length of immediate texts
       Subfun of process_article
    """
    article_tags = article_body_root.find_all(recursive=recursive)
    for article_tag in article_tags:
        tag_name = to_friendly(article_tag, excluded_tags_fun)
        tag_dict[tag_name][0] += 1
        tag_dict[tag_name][1] += len(article_tag.text.strip().split())
        tag_dict[tag_name][2] += len(article_tag.find_all())
        tag_dict[tag_name][3].add(article_url)
        tag_dict[tag_name][4] += immediate_text(article_tag)


def final_summarize_children_or_subtree(dates, out_files, tag_dict, tei_logger):
    """Produce the final form of the aggregated information after a WARC has been processed into text or notext tables:
        - the frequency for each tag
        - the name and attributes of the root tag
        - the average word count of all the texts it contains
        - the average number of descendant tags
        - the average length of immediate texts
        - the URLs of some random occurrences
        - the placeholder for normal name of tag
        - the placeholder for preserved attribute name
    """
    _ = dates, tei_logger  # Silence IDE
    out_notext_fh, out_text_fh = out_files
    print('frequency', 'tag', 'average_word_count', 'average_descendant_num', 'immediate_texts_average_length',
          'URL_example', 'normal_name', 'preserved_attribute', sep='\t', file=out_text_fh)
    print('frequency', 'tag', 'average_word_count', 'average_descendant_num', 'immediate_texts_average_length',
          'URL_example', 'normal_name', 'preserved_attribute', sep='\t', file=out_notext_fh)
    for root_name_attr, (freq, no_of_words, no_of_descendants, all_links, len_of_immediate_text) in tag_dict.items():
        random_links = random_sample(all_links, k=min(5, len(all_links)))
        example_links = ' '.join(random_links)
        avg_no_of_words = no_of_words / freq
        avg_no_of_descendants = no_of_descendants / freq
        avg_len_of_immediate_text = len_of_immediate_text / freq
        if avg_no_of_words == 0:
            category = 'null'
            out_file = out_notext_fh
        else:
            category = 'default'
            out_file = out_text_fh
        rename = 'default'
        print(freq, root_name_attr, avg_no_of_words, avg_no_of_descendants, avg_len_of_immediate_text, example_links,
              category, rename, sep='\t', file=out_file)


def init_portal(log_dir, output_dir, run_params, portal_name, tei_logger, warc_level_params, rest_config_params):
    """Init variables for processing a portal: Tag Inventory Maker (This is the only public function of this file)"""
    _ = log_dir, warc_level_params  # Silence IDE

    article_root_params, decompose_spec, excluded_tags_spec = rest_config_params[1:4]

    recursive = run_params.get('recursive')
    if recursive is None:
        tei_logger.log('CRITICAL', 'recursive is not set in run_params!')
        exit(1)

    # The internal structure of the accumulator is defined in summarize_children_or_subtree function
    accumulator = defaultdict(lambda: [0, 0, 0, set(), 0])
    # No files and after processing needed for each article
    after_article_fun, after_article_params, log_file_names_and_modes = dummy_fun, (), ()
    # Filenames for the final function
    final_filenames_and_modes = ((os_path_join(output_dir, f'{portal_name}_notext_tags_normal.tsv'), 'w'),
                                 (os_path_join(output_dir, f'{portal_name}_text_tags_normal.tsv'), 'w'))
    # Run this function after all articles are processed
    final_fun = final_summarize_children_or_subtree
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
    #  - the parameters for the subfunction
    process_article_params = (tei_logger, article_root_params, decompose_spec, excluded_tags_spec,
                              summarize_children_or_subtree, (accumulator, recursive))
    # Runner function (some task can be run only in single-process mode)
    run_fun = run_single_process

    return accumulator, after_article_fun, after_article_params, log_file_names_and_modes, final_filenames_and_modes, \
        final_fun, process_article_fun, process_article_params, run_fun
