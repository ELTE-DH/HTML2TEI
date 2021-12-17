#!/usr/bin/env python3
# -*- coding: utf-8, vim: expandtab:ts=4 -*-

from copy import copy
from collections import defaultdict
from uuid import uuid5, NAMESPACE_URL
from os.path import join as os_path_join
from datetime import datetime, MAXYEAR, MINYEAR

from bs4 import BeautifulSoup

from html2tei.tei_utils import create_new_tag_with_string
from html2tei.validate_hash_zip import init_output_writer
from html2tei.processing_utils import run_single_process, run_multiple_process

DUPL_METAS = {'sch:keywords', 'sch:author', 'sch:contentLocation', 'sch:artist', 'sch:source'}


def tei_writer(warc_date, warc_id, xml_string, meta_data, article_body_contents, multipage_warc_datas=None):
    """
    Function for writing an article into a file in TEI format
     The input dictionary is used to generate tags from key-value pairs except special keys which are handled separately
    :param warc_date:
    :param warc_id:
    :param xml_string:
    :param meta_data: a prepared dictionary contains the meta-data to be written
    :param article_body_contents: a list of Tag()-s which is written without further examination.
       Note: Individual subtrees must be cleaned before this function!
    :param multipage_warc_datas
    """
    url = meta_data['sch:url']
    art_date_pub = meta_data['sch:datePublished']
    # FILENAME + TEIPID
    # 1. TEI PID generation
    tei_pid = str(uuid5(NAMESPACE_URL, f'{url} {warc_date}'))
    # 2. Filename production (organized in a date folder)
    if art_date_pub is not None:
        art_date_pub_fn = art_date_pub.date().isoformat()
        meta_data['sch:datePublished'] = art_date_pub.isoformat()
    else:
        art_date_pub_fn = 'unknown_date'
    art_date_mod = ''
    if 'sch:dateModified' in meta_data.keys():
        art_date_mod = meta_data['sch:dateModified'].isoformat()
        meta_data['sch:dateModified'] = art_date_mod
    final_name = os_path_join(str(art_date_pub_fn), tei_pid)
    final_suff = '.xml'
    article_author = None
    article_title = meta_data['sch:name']
    if 'sch:author' in meta_data.keys():
        article_author = meta_data['sch:author']
    beauty_xml = BeautifulSoup(xml_string, features='lxml-xml')

    # TEI <fileDesc>
    file_title = beauty_xml.find('titleStmt')
    if article_title is not None:
        file_title = beauty_xml.find('titleStmt')
        file_title.title.string = article_title
    idno = beauty_xml.find('idno')
    idno.string = str(tei_pid)

    # Adding the writer in the code below because it should be in sourceDesc in the same way
    if 'sch:source' in meta_data.keys():
        for one_source in meta_data['sch:source']:
            org_tag = beauty_xml.new_tag('orgName')
            org_tag.string = one_source
            source_org_root = beauty_xml.new_tag('respStmt')
            source_org_root.append(beauty_xml.new_tag('resp'))
            source_org_root.append(org_tag)
            file_title.append(source_org_root)

    # TEI <sourceDesc><bibl>
    sourcedesc = beauty_xml.find('sourceDesc')
    source_date_tag = sourcedesc.find_all('date')[2]
    if art_date_pub is not None:
        source_date_tag.attrs = {'when': art_date_pub.isoformat()}
    else:
        source_date_tag.attrs = {'when-custom': 'unknown'}
    if article_title is not None:
        sourcedesc.title.string = article_title
    if article_author is not None and len(article_author) != 0:
        for author_name in article_author:
            author_tag = beauty_xml.new_tag('author')
            one_name = beauty_xml.new_tag('persName')
            one_name.string = author_name.strip()
            author_tag.append(one_name)
            file_title.append(author_tag)
            sourcedesc_author = copy(author_tag)
            sourcedesc.find('title').insert_after(sourcedesc_author)

    # XENODATA 1: metadata of article source
    xeno_meta_datas = beauty_xml.find('rdf:Description')
    xeno_meta_datas.attrs['rdf:about'] = url
    for k, v in meta_data.items():
        if v is not None:
            if k == 'subsection':
                one_meta = beauty_xml.new_tag('sch:articleSection')
                one_meta.string = v
                xeno_meta_datas.find('sch:articleSection').append(one_meta)
            elif k in DUPL_METAS:
                for dupl in v:
                    create_new_tag_with_string(beauty_xml, dupl, k, xeno_meta_datas)
            else:
                create_new_tag_with_string(beauty_xml, v, k, xeno_meta_datas)

    # XENODATA 2: warc data
    xeno_tei_rdf = ''
    for rdf in beauty_xml.find_all('rdf:Description'):
        if rdf.attrs['rdf:about'] == 'teiPid':
            xeno_tei_rdf = rdf
            rdf.attrs['rdf:about'] = tei_pid

    # XENO 3: TEI file data + article warc response data
    xeno_tei_rdf.find('sch:identifier').string = warc_id[1:-1]
    current_time = datetime.today().isoformat()
    xeno_tei_rdf.find('sch:sdDatePublished').string = current_time
    warc_date_string = warc_date.isoformat()
    xeno_tei_rdf.find('sch:lastReviewed').string = warc_date_string

    # revisionDesc
    revision_desc = beauty_xml.find('revisionDesc')
    # Default change tag is already present in the XML skeleton
    change = revision_desc.change
    change.attrs['when'] = current_time
    change.attrs['source'] = tei_pid
    if 'sch:dateModified' in meta_data.keys():
        change_art_modified = beauty_xml.new_tag('change', when=art_date_mod, source=url)
        change_art_modified.string = 'article modified'
        revision_desc.append(change_art_modified)

    # FILL TEI BODY
    body = beauty_xml.body
    if article_title is None:
        article_title = 'unknown'
    article_title_tag = beauty_xml.new_tag('head', type='title')
    article_title_tag.string = article_title
    body.append(article_title_tag)
    if 'sch:alternateName' in meta_data.keys():
        article_alternate_title = meta_data['sch:alternateName']
        article_subtitle_tag = beauty_xml.new_tag('head', type='subtitle')
        article_subtitle_tag.string = article_alternate_title
        body.append(article_subtitle_tag)
    if article_body_contents == 'EMPTY ARTICLE':
        tei_change = beauty_xml.find('change', source=True)
        empty_body_note = beauty_xml.new_tag('note')
        tei_change.append(empty_body_note)
        empty_body_note.string = 'A cikk tartalma az archiválás pillanatában nem volt elérhető./' \
                                 'The content of the article was not available at the time of archiving.'
        body.append(beauty_xml.new_tag('p'))
    elif isinstance(article_body_contents, list):
        for i, main_subtrees in enumerate(article_body_contents):
            if main_subtrees.name == 'div' and 'type' in main_subtrees.attrs.keys() and \
                    main_subtrees.attrs['type'] == 'comments_container':
                main_subtrees.attrs['corresp'] = tei_pid
                main_subtrees.attrs['source'] = url
                break
        body.extend(article_body_contents)
    elif isinstance(article_body_contents, dict):
        for url, page_contents in article_body_contents.items():
            div = beauty_xml.new_tag('div')
            div.attrs = {'source': url, 'type': 'page'}
            div.extend(page_contents)
            body.append(div)
    if multipage_warc_datas is not None:
        note_tag = beauty_xml.new_tag('note')
        note_tag.string = 'WARC response data per URL:'
        for url_k, (w_id, w_d) in multipage_warc_datas.items():
            note_p = beauty_xml.new_tag('p')
            create_new_tag_with_string(beauty_xml, url_k, 'ref', note_p)
            create_new_tag_with_string(beauty_xml, w_id[1:-1], 'idno', note_p)
            create_new_tag_with_string(beauty_xml, w_d.isoformat(), 'date', note_p)
            note_tag.append(note_p)
        tei_change = beauty_xml.find('change', source=True)
        tei_change.append(note_tag)
    pretty_xml = beauty_xml.prettify().encode('UTF-8')
    return final_name, final_suff, pretty_xml, art_date_pub


def merge_multipage_article_metadata(multipage_article):
    """Combine metadata and body collected from different pages of multi-page articles"""
    all_warc_datas_tup_for_note = {}
    converted_body_dict = {}
    for _, converted_body, (act_url, warc_response_datetime, warc_id, _) in multipage_article:
        all_warc_datas_tup_for_note[act_url] = (warc_id, warc_response_datetime)
        converted_body_dict[act_url] = converted_body
    # All metadata will be merged
    merged_meta_dict = {}
    meta_name_cache = defaultdict(set)
    min_pub = datetime(MAXYEAR, 1, 1)
    max_pub = datetime(MINYEAR, 1, 1)
    max_mod = datetime(MINYEAR, 1, 1)
    for metas, *_ in multipage_article:
        for meta_name, meta_values in metas.items():
            if isinstance(meta_values, datetime):
                if meta_name == 'sch:datePublished':
                    min_pub = min(min_pub, meta_values)
                    max_pub = max(max_pub, meta_values)
                elif meta_name == 'sch:dateModified':
                    max_mod = max(max_mod, meta_values)
            elif meta_name not in merged_meta_dict.keys():
                merged_meta_dict[meta_name] = meta_values
            elif isinstance(meta_values, list):
                valami = meta_name_cache[meta_name]
                for meta_value in meta_values:
                    if meta_value not in valami:
                        valami.add(meta_value)
                        merged_meta_dict[meta_name].append(meta_value)
    if min_pub != datetime(MAXYEAR, 1, 1):
        merged_meta_dict['sch:datePublished'] = min_pub
    if max_mod != datetime(MINYEAR, 1, 1):
        merged_meta_dict['sch:dateModified'] = max_mod
    if 'sch:dateModified' not in merged_meta_dict.keys():
        merged_meta_dict['sch:dateModified'] = max_pub
    return merged_meta_dict, converted_body_dict, all_warc_datas_tup_for_note


def process_multipage_article(article_tup_list, process_article_and_spec_params):
    """Process the pages of multi-page articles one after the other"""
    # Get the url, WARC response date and WARC ID for the first page of the article
    first_url, first_article_warc_resp_date, first_article_warc_id, _ = article_tup_list[0]
    (tei_logger, base_xml_string, get_meta_fun, write_out_mode), spec_body_params = process_article_and_spec_params
    multipage_article = []
    for article_tup in article_tup_list:
        # Pass to the paragraph extractor function and collect WARC metadata to list
        metas_in_dict, converted_body = write_out_mode(article_tup, tei_logger, get_meta_fun, spec_body_params)
        multipage_article.append((metas_in_dict, converted_body, article_tup))

    merged_meta_dict, converted_body_dict, all_warc_datas_tup_for_note = \
        merge_multipage_article_metadata(multipage_article)
    return first_url, first_article_warc_resp_date, first_article_warc_id, base_xml_string, merged_meta_dict, \
        converted_body_dict, all_warc_datas_tup_for_note


def process_article_clean(params):
    """This function is the first to receive data from the generator (aggregated_multipage_articles_gen)
        for each article (single-page or multi-page)
       This function should do processing that does allow parallel processing to make the conversion faster,
       The after_clean function is for doing tasks sequentially after processing each individual articles
        (e.g. writing the output to files)
    """
    article_tup_list, process_article_and_spec_params = params
    converted_body, tei_data = None, (None, None, None, None)
    if len(article_tup_list) == 1:  # Process single-page article
        (tei_logger, base_xml_string, get_meta_fun, write_out_mode), spec_body_params = process_article_and_spec_params
        first_page_of_article = article_tup_list[0]
        first_url, warc_response_datetime, warc_id, raw_html = first_page_of_article

        metas_in_dict, converted_body = write_out_mode(first_page_of_article, tei_logger, get_meta_fun,
                                                       spec_body_params)
        all_warc_datas_tup_for_note = None
    else:  # Process multi-page article
        # write_out_mode is passed into process_multipage_article with process_article_and_spec_params
        # The different write_out_mode implementations are defined in article_body_converters
        # Multipage articles:
        #  - URL from the first page
        #  - WARC response datetime from the first page
        #  - WARC ID from the first page
        #  - the base TEI XML string for the portal (we use this version for simplicity)
        #  - Metas are merged
        #  - The converted body (extracted paragraphs)
        #  - Extra: All WARC data are collected for '<note>'-ing in TEI
        first_url, warc_response_datetime, warc_id, base_xml_string, metas_in_dict, converted_body, \
            all_warc_datas_tup_for_note = process_multipage_article(article_tup_list, process_article_and_spec_params)
    # Create TEI XML if the conversion was successful
    if metas_in_dict is not None and converted_body is not None:
        tei_data = tei_writer(warc_response_datetime, warc_id, base_xml_string, metas_in_dict, converted_body,
                              all_warc_datas_tup_for_note)

    return first_url, tei_data


def after_clean(ret, validator_hasher_compressor, file_handles):
    """This function write the processed article (process_article_clean, tei_writer) into the output:
        - the URL to the url_list or bad_article_urls file
        - the XML to the validator_hasher_compressor
       The input parameters are the url and the output of tei_writer.
       The function returns the extracted publish_date or None if no tei_string could be extracted
    """
    url, (desired_filename, filename_suff, tei_string, publish_date) = ret
    url_list, bad_article_urls, date_container = file_handles
    if tei_string is not None:
        final_filename = validator_hasher_compressor.process_one_file(url, desired_filename, filename_suff, tei_string)
        print(url, final_filename, file=url_list)
        if publish_date is not None:
            return publish_date
    else:
        print(url, file=bad_article_urls)


def final_clean(dates, out_files, warc_date_interval, tei_logger):
    """Produce the final form of the aggregated information after a WARC has been processed: dates into the logger"""
    date_min, date_max = dates
    _ = out_files  # Silence IDE
    if date_max != datetime(MINYEAR, 1, 1) and date_min != datetime(MAXYEAR, 1, 1):
        tei_logger.log('INFO', 'first date:', date_min.isoformat())
        tei_logger.log('INFO', 'last date:', date_max.isoformat())
    tei_logger.log('INFO', 'warc first date:', warc_date_interval['date_min'])
    tei_logger.log('INFO', 'warc last date:', warc_date_interval['date_max'])


def init_portal(log_dir, output_dir, run_params, portal_name, tei_logger, warc_level_params, rest_config_params):
    """Init variables for processing a portal: Portal Article Cleaner (This is the only public function of this file)"""

    output_debug = run_params.get('output_debug')
    if output_debug is None:
        tei_logger.log('CRITICAL', 'output_debug is not set in run_params!')
        exit(1)

    run_parallel = run_params.get('run_parallel')
    if run_parallel is None:
        tei_logger.log('CRITICAL', 'run_parallel is not set in run_params!')
        exit(1)

    if not run_params.get('w_specific_dicts', False) or not run_params.get('w_specific_tei_base_file', False):
        tei_logger.log('CRITICAL', 'w_specific_dicts and w_specific_tei_base_file are must set to True in run_params!')
        exit(1)

    get_meta_fun_spec, article_root_params, decompose_spec, excluded_tags_spec, portal_url_prefix, \
        portalspec_link_filter, links, block_rules_spec, bigram_rules_spec, tag_normal_dict, \
        portal_specific_block_rules, portal_xml_string, write_out_mode = rest_config_params

    # The internal structure of the accumulator is defined in read_portalspec_config function
    # Get a reference to warc_date_interval to be able to use without returning it in the generator
    #  (aggregated_multipage_articles_gen)
    accumulator = warc_level_params[4]
    # The function to run after processing each article with process_article_clean
    #  (involves writing to files, which must be done sequentially even if the rest is done in parallel)
    after_article_fun = after_clean
    # The only extra parameter for after_article_fun is the output writer class (validator-hasher-compressor)
    after_article_params = init_output_writer(output_dir, portal_name, output_debug, tei_logger)
    # The filenames (and modes) to be written into in after_article_fun
    log_file_names_and_modes = ((os_path_join(log_dir, f'{portal_name}_urls.txt'), 'a'),
                                (os_path_join(log_dir, f'{portal_name}_bad_urls.txt'), 'a'),
                                (os_path_join(log_dir, f'{portal_name}_date_container.txt'), 'a'))
    # Filenames for the final function
    final_filenames_and_modes = ()
    # Run this function after all articles are processed
    final_fun = final_clean
    # Process articles one by one with this function
    process_article_fun = process_article_clean
    # Task specific params (process_article_clean):
    #  - the TEI logger initialised
    #  - the portal-specific base TEI XML in string format
    #  - the portal-specific get_meta function
    #  - the write-out mode (e.g. Custom Article Body Converter, JusText, Newspaper3k)
    process_article_clean_params = [tei_logger, portal_xml_string, get_meta_fun_spec, write_out_mode]  # Must be list!
    # Params for write_out_mode from the loaded portal-specific configuration
    # The different write_out_mode implementations are defined in article_body_converters"
    #  - article root params for find_all
    #  - portal-specific decompose functions
    #  - portal-specific simplification rules for the different parts of the attributes,
    #     with merging the irrelevant variations of values
    #  - tag_normal_dict the normalized names of the tags mapped to the simplified tagnames
    #  - links tagnames which could contain attributes to be preserved to help later disambiguation (div, etc.)
    #  - portal_specific_block_rules portal-specific block renaming rules
    #  - bigram_rules_spec portal-specific bigram rules
    #  - portal_url_prefix the url prefix of the portal (e.g. domain name for relative links)
    #  - portalspec_link_filter substring list to filter non-repairable links
    portalspec_params_and_dicts = (article_root_params, decompose_spec, excluded_tags_spec,
                                   tag_normal_dict, links, portal_specific_block_rules, bigram_rules_spec,
                                   portal_url_prefix, portalspec_link_filter)
    process_article_params = (process_article_clean_params, portalspec_params_and_dicts)

    # Runner function (some task can be run only in single-process mode)
    if run_parallel:
        run_fun = run_multiple_process
    else:
        run_fun = run_single_process

    return accumulator, after_article_fun, after_article_params, log_file_names_and_modes, final_filenames_and_modes, \
        final_fun, process_article_fun, process_article_params, run_fun
