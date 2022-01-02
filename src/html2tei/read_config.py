# !/usr/bin/env python3
# -*- coding: utf-8, vim: expandtab:ts=4 -*-

import sys
import importlib.util
from copy import deepcopy
from argparse import Namespace
from collections import Counter
from os.path import join as os_path_join, isfile, isdir, abspath, dirname

from lxml import etree
from webarticlecurator import Logger
from yaml import load as yaml_load, SafeLoader

from html2tei.basic_tag_dicts import BLOCK_RULES

# Only read_portalspec_config and read_input_config is used outside of this file


def check_exists(filesystem_path, tei_logger=None, check_fun=isfile, message='File not found'):
    """Common helper function to check if file/directory exists"""
    if tei_logger is None:
        tei_logger = Namespace(log=print)  # Hack, dummy logger! ;)
    if not check_fun(filesystem_path):
        # File argument is necessary for the dummy logger
        tei_logger.log('CRITICAL', f'{message}: {filesystem_path}', file=sys.stderr)
        exit(1)


def load_portal_specific_dicts(text_tags_normal_fn, notext_tags_normal_fn, portal_specific_block_rules, tei_logger):
    """Load portal_specific TSV files (text and notext) into dictionaries.
    The header is kept in the dictionary, as it differs from the other keys (HTML tags) therefore it is ignored."""
    with open(text_tags_normal_fn, encoding='UTF-8') as text_tags_dict, \
            open(notext_tags_normal_fn, encoding='UTF-8') as notext_tags_dict:
        portal_tags_to_normal = {}
        for current_file, fn in ((text_tags_dict, text_tags_normal_fn), (notext_tags_dict, notext_tags_normal_fn)):
            for line_no, line in enumerate(current_file):
                try:
                    # One row consists of frequency, the freezed tag (tag name and attributes),
                    # the avg. len. of the texts, the avg no. of tags it contains,
                    # the avg. len. of the immediate texts, the URLs of some random occurrences,
                    # and the normalized name and preserved attributes for each tag.
                    # Here only freezed tag and normal(ized) name and the preserved attributes will be used
                    _, freezed_tag, _, _, _, _, normal_name, preserved_attribute, *_ = \
                        (col.strip() for col in line.strip().split('\t'))
                except ValueError:
                    tei_logger.log('CRITICAL', f'{fn} at line {line_no}: the number of fields does not match!')
                    exit(1)
                portal_tags_to_normal[freezed_tag] = '\t'.join([normal_name, preserved_attribute])
    merged_portal_specific_block_rules = deepcopy(BLOCK_RULES)
    for block_key, block_value in portal_specific_block_rules.items():
        for three_key, t_value in block_value.items():
            merged_portal_specific_block_rules[block_key][three_key] = t_value
    return portal_tags_to_normal, merged_portal_specific_block_rules


def get_portal_spec_fun_and_dict_names(module_fn, tei_logger):
    """Load portal the specific configuration (python) file and check for the required arguments"""
    try:
        portal_spec_module = import_python_file('portal_spec', module_fn)
    except SyntaxError as fun_or_const:
        tei_logger.log('CRITICAL', f'Could not load config file: SyntaxError: {fun_or_const}')
        exit(1)
        portal_spec_module = None  # Silence dummy IDE

    portal_speicific_funs_and_constants = []
    for fun_or_const in ('BLACKLIST_SPEC', 'MULTIPAGE_URL_END', 'next_page_of_article_spec',
                         'get_meta_from_articles_spec', 'ARTICLE_ROOT_PARAMS_SPEC', 'decompose_spec',
                         'excluded_tags_spec', 'PORTAL_URL_PREFIX', 'LINK_FILTER_SUBSTRINGS_SPEC', 'LINKS_SPEC',
                         'BLOCK_RULES_SPEC', 'BIGRAM_RULES_SPEC'):
        e_loaded = getattr(portal_spec_module, fun_or_const)
        if fun_or_const is None:
            tei_logger.log('CRITICAL', f'Missing elem from config file ({module_fn}): {fun_or_const} !')
            exit(1)
        portal_speicific_funs_and_constants.append(e_loaded)

    return portal_speicific_funs_and_constants


def read_portal_tei_base_file(tei_base_dir_and_name, tei_logger):
    """Read TEI XML base to be extended for the specific articles
        as it is not valid TEI XML at this point we can check only its well-formedness"""
    with open(tei_base_dir_and_name, encoding='UTF-8') as xml_base:
        portal_xml_string = xml_base.read()
    try:
        etree.fromstring(portal_xml_string.encode('UTF-8'))
    except etree.XMLSyntaxError:
        tei_logger.log('CRITICAL', f'{tei_base_dir_and_name} is not well-formed XML!')
        exit(1)
    return portal_xml_string


def import_python_file(module_name, file_path):
    """Import module from file: https://docs.python.org/3/library/importlib.html#importing-a-source-file-directly"""
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


dirname_of_abcs = os_path_join(dirname(abspath(__file__)), 'article_body_converters')
WRITE_OUT_MODES = {'eltedh': os_path_join(dirname_of_abcs, 'eltedh_abc.py'),
                   'justext': os_path_join(dirname_of_abcs, 'justext_abc.py'),
                   'newspaper3k': os_path_join(dirname_of_abcs, 'newspaper_abc.py')}


def read_portalspec_config(configs_dir, portal_name, warc_dir, warc_name, log_dir, run_params=None,
                           logfile_level='INFO', console_level='INFO'):
    """Read and validate all input files and runtime parameters"""

    if run_params is None:
        run_params = {}

    # Init logfile
    log_filename = os_path_join(log_dir, f'tei_writing_{portal_name}.log')
    check_exists(log_dir, check_fun=isdir, message='Directory not found')
    tei_logger = Logger(log_filename=log_filename, logfile_mode='w', logfile_level=logfile_level,
                        console_level=console_level)

    task_name = run_params.get('task_name')
    if task_name is None:
        tei_logger.log('CRITICAL', 'task_name is not set in run_params!')
        exit(1)

    tei_logger.log('INFO', f'Running {task_name}')
    tei_logger.log('INFO', f'Processing {portal_name}')

    # Portal specific config (python) stuff
    portal_spec_module_fn = os_path_join(configs_dir, portal_name, f'{portal_name}_specific.py')
    check_exists(portal_spec_module_fn, tei_logger)
    blacklist_spec, multipage_compile, next_page_of_article_fun, get_meta_fun_spec, article_root_params, \
        decompose_spec, excluded_tags_spec, portal_url_prefix, link_filter_spec, links, block_rules_spec, \
        bigram_rules_spec = get_portal_spec_fun_and_dict_names(portal_spec_module_fn, tei_logger)

    # WARC reading stuff
    warc_name = os_path_join(warc_dir, warc_name)
    check_exists(warc_name, tei_logger)

    warc_date_interval = {}  # Actually the maximal date interval for HTTP responses in the WARC file
    warc_level_params = (warc_name, blacklist_spec, multipage_compile, tei_logger, warc_date_interval,
                         next_page_of_article_fun)

    # Portal specific TSV dictionaries stuff
    if run_params.get('w_specific_dicts', False):
        tei_logger.log('INFO', 'Loading portal specific dicts')
        text_tags_normal_fn = os_path_join(configs_dir, portal_name, f'{portal_name}_text_tags_normal.tsv')
        check_exists(text_tags_normal_fn, tei_logger)
        notext_tags_normal_fn = os_path_join(configs_dir, portal_name, f'{portal_name}_notext_tags_normal.tsv')
        check_exists(notext_tags_normal_fn, tei_logger)

        tag_normal_dict, portal_specific_block_rules = \
            load_portal_specific_dicts(text_tags_normal_fn, notext_tags_normal_fn, block_rules_spec,
                                       tei_logger)
    else:
        tei_logger.log('INFO', 'Not loading portal specific dicts')
        tag_normal_dict, portal_specific_block_rules = None, None

    # Base TEI XML file reading stuff
    if run_params.get('w_specific_tei_base_file', False):
        tei_logger.log('INFO', 'Loading portal specific TEI base file')
        tei_base_dir_and_name = os_path_join(configs_dir, portal_name, f'{portal_name}_BASE.xml')
        check_exists(tei_base_dir_and_name, tei_logger)
        portal_xml_string = read_portal_tei_base_file(tei_base_dir_and_name, tei_logger)
    else:
        tei_logger.log('INFO', 'Not loading portal specific TEI base file')
        portal_xml_string = None

    write_out_mode = run_params.get('write_out_mode')
    write_out_mode_fun = None
    write_out_mode_file = WRITE_OUT_MODES.get(write_out_mode)
    if write_out_mode is not None and write_out_mode_file is None:
        tei_logger.log('CRITICAL', f'{write_out_mode} is not in the allowed value set ({set(WRITE_OUT_MODES.keys())})!')
        exit(1)
    elif write_out_mode is not None:
        # Here we import optional libraries only if they are needed later
        write_out_mode_fun = getattr(import_python_file('article_body_converters', write_out_mode_file),
                                     'process_article')
        tei_logger.log('INFO', f'Using {write_out_mode} write mode')

    return tei_logger, warc_level_params, get_meta_fun_spec, article_root_params, decompose_spec, excluded_tags_spec, \
        portal_url_prefix, link_filter_spec, links, block_rules_spec, bigram_rules_spec, tag_normal_dict, \
        portal_specific_block_rules, portal_xml_string, write_out_mode_fun


def read_input_config(warc_filename):
    """Read the input YAML file containing a dictionary of WARC filename - portal name mapping"""
    check_exists(warc_filename)
    warc = yaml_load(open(warc_filename, encoding='UTF-8'), Loader=SafeLoader)
    portal_name_count = Counter()
    for portal_name in warc.values():
        portal_name_count[portal_name] += 1
    duplicate = [portal_name for portal_name, freq in portal_name_count.items() if freq > 1]
    if len(duplicate) > 0:
        print(f'CRITICAL: {warc_filename} contains duplicate portal names ({duplicate})!')
        exit(1)
    return warc.items()
