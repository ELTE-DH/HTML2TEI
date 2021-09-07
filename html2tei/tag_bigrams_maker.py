#!/usr/bin/env python3
# -*- coding: utf-8, vim: expandtab:ts=4 -*-

from collections import defaultdict
from os.path import join as os_path_join
from random import sample as random_sample

from html2tei.tei_utils import to_friendly
from html2tei.processing_utils import run_single_process, dummy_fun, process_article


def summarize_tag_bigrams(tag_dict, mode_recursive, article_url, article_body_root, excluded_tags_fun):
    """This function summarizes the properties of each occurrence of the tags (direct or all descendants as bigrams):
        - frequency for each bigram (if there is no child tag the second part of the bigram will be 'TEXT')
        - the URLs of (some random) occurrences
    """
    for a in article_body_root.find_all():  # First part of the bigram (a)
        a_name = to_friendly(a, excluded_tags_fun)
        a_tag_type_descendants = a.find_all(recursive=mode_recursive)
        if len(a_tag_type_descendants) == 0:
            a_b_name = '{0}\tTEXT'.format(a_name)
            (frequency, urls) = tag_dict[a_b_name]
            tag_dict[a_b_name][0] = frequency + 1
            tag_dict[a_b_name][1].add(article_url)

        else:
            for b in a_tag_type_descendants:  # Second part of the bigram (b) all descendants
                a_b_name = '{0}\t{1}'.format(a_name, to_friendly(b, excluded_tags_fun))
                (frequency, urls) = tag_dict[a_b_name]
                tag_dict[a_b_name][0] = frequency + 1
                tag_dict[a_b_name][1].add(article_url)


def final_bigram(dates, out_files, tag_dict, tei_logger):
    """Produce the final form of the aggregated information after a WARC has been processed into the table:
        - the frequency for each tag bigram
        - the name and attributes of the root tag
        - the URLs of some random occurrences
    """
    _ = dates, tei_logger  # Silence IDE
    out_file = out_files[0]
    for root_name_attr, (freq, all_links) in tag_dict.items():
        random_links = random_sample(all_links, k=min(5, len(all_links)))
        example_links = ' '.join(random_links)
        print(freq, root_name_attr, example_links, sep='\t', file=out_file)


def init_portal(log_dir, output_dir, run_params, portal_name, tei_logger, warc_level_params, rest_config_params):
    """Init variables for processing a portal: Tag Bigrams Maker (This is the only public function of this file)"""
    _ = log_dir, warc_level_params  # Silence IDE

    article_root_params, decompose_spec, excluded_tags_spec = rest_config_params[1:4]

    recursive = run_params.get('recursive')
    if recursive is None:
        tei_logger.log('CRITICAL', 'recursive is not set in run_params!')
        exit(1)

    # The internal structure of the accumulator is defined in summarize_tag_bigrams function
    accumulator = defaultdict(lambda: [0, set()])
    # No files and after processing needed for each article
    after_article_fun, after_article_params, log_file_names_and_modes = dummy_fun, (), ()
    # Filenames for the final function
    final_filenames_and_modes = ((os_path_join(output_dir, f'{portal_name}_bigrams.tsv'), 'w'),)
    # Run this function after all articles are processed
    final_fun = final_bigram
    # Process articles one by one with this function
    process_article_fun = process_article
    # From the loaded portal-specific configuration
    #  - TEI logger for logging
    #  - article root params for find all variation of the range of useful parts of articles
    #  - portal-specific decompose functions
    #  - portal-specific simplification rules for the different parts of the attributes,
    #     with merging the irrelevant variations of values
    # Task specific params:
    #  - (sub)function to run after cleaning the article up (decompose unnecessary parts)
    #  - the parameters for the subfunction
    process_article_params = (tei_logger, article_root_params, decompose_spec, excluded_tags_spec,
                              summarize_tag_bigrams, (accumulator, recursive))
    # Runner function (some task can be run only in single-process mode)
    run_fun = run_single_process

    return accumulator, after_article_fun, after_article_params, log_file_names_and_modes, final_filenames_and_modes, \
        final_fun, process_article_fun, process_article_params, run_fun
