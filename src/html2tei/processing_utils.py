# !/usr/bin/env python3
# -*- coding: utf-8, vim: expandtab:ts=4 -*-


from multiprocessing import Pool, Manager
from contextlib import contextmanager
from os.path import isdir as os_path_isdir
from threading import Lock as threading_Lock
from datetime import datetime, MINYEAR, MAXYEAR
from locale import setlocale, LC_ALL, Error as locale_Error

from bs4 import BeautifulSoup
from webarticlecurator import WarcCachingDownloader

from html2tei.unicode_error import unicode_test
from html2tei.read_config import check_exists, read_input_config, read_portalspec_config


def extract_resp_record_data(resp):
    """Extract response date, WARC ID and raw HTML from a WARC response record"""
    warc_response_date = resp.rec_headers.get_header('WARC-Date')
    if '.' in warc_response_date:
        date_format = '%Y-%m-%dT%H:%M:%S.%fZ'
    else:
        date_format = '%Y-%m-%dT%H:%M:%SZ'
    warc_response_datetime = datetime.strptime(warc_response_date, date_format)
    warc_id = resp.rec_headers.get_header('WARC-Record-ID')
    raw_html = resp.content_stream().read().decode(resp.rec_headers.get_header('WARC-X-Detected-Encoding'))

    return warc_response_datetime, warc_id, raw_html


def aggregated_multipage_articles_gen(warc_level_params, run_parameters):
    """Create a generator of article, response date, WARC ID, raw HTML tuples
       where multi-page articles are treated as one entry
    """
    # We use these variables here, the others are passed blindly to the other processing levels
    warc_filenames, blacklist, multipage_compile, warc_logger, date_interval, next_page_of_article_fun \
        = warc_level_params

    # Init WARC cache
    warc_reader = WarcCachingDownloader(warc_filenames, None, warc_logger, just_cache=True,
                                        download_params={'strict_mode': True, 'check_digest': True})
    # Set defaults
    date_max = datetime(MINYEAR, 1, 1)
    date_min = datetime(MAXYEAR, 1, 1)

    for article_url in warc_reader.url_index:
        if article_url in blacklist or multipage_compile.match(article_url):
            continue
        # Articles first pages not on blacklist
        article = []
        while article_url is not None:
            # Process URL and append page data to article list
            _, _, resp = warc_reader.get_records(article_url)  # From WebArticleCurator
            warc_response_datetime, warc_id, raw_html = extract_resp_record_data(resp)
            date_min = min(date_min, warc_response_datetime)
            date_max = max(date_max, warc_response_datetime)
            article.append((article_url, warc_response_datetime, warc_id, raw_html))

            # Generate next page URL
            article_url = next_page_of_article_fun(raw_html)

            if article_url is None or article_url in blacklist:
                article_url = None
            elif article_url not in warc_reader.url_index:
                article_url = None
                warc_logger.log('CRITICAL', f'The next_page URL {article_url} does not present'
                                            f' in the archive {warc_filenames}!')

        yield article, run_parameters  # Return the gathered article

    # Return the computed date interval to the cally by modifying the parameter
    date_interval['date_min'] = date_min
    date_interval['date_max'] = date_max


@contextmanager
def open_multiple_files(args):
    """A helper function to open multiple files at once in a contextmanager"""
    opened_files = []
    try:
        for filename, mode in args:
            opened_files.append(open(filename, mode, encoding='UTF-8'))
        yield opened_files
    finally:
        for fh in opened_files:
            fh.close()


# This function is used outside of this file
def run_single_process(warc_filename, file_names_and_modes, main_function, sub_functions, after_function, after_params):
    """Read a WARC file and sequentially process all articles in it with main_function
        (multi-page articles are handled as one entry) and yield the result after filtered through after_function
    """
    with open_multiple_files(file_names_and_modes) as fhandles:
        for params in aggregated_multipage_articles_gen(warc_filename, sub_functions):
            ret = main_function(params)
            yield after_function(ret, after_params, fhandles)


# This function is used outside of this file
def run_multiple_process(warc_filename, file_names_and_modes, main_function, sub_functions, after_function,
                         after_params):
    """Read a WARC file and sequentially process all articles in it with main_function in parallel preserving ordering
        (multi-page articles are handled as one entry) and yield the result after filtered through after_function
    """
    # This is parallel as it computes each page separately. Order preserved!
    with Manager() as man:
        log_queue = man.Queue()
        logger_obj = sub_functions[0][0]
        with logger_obj.init_mp_logging_context(log_queue) as mp_logger, \
                open_multiple_files(file_names_and_modes) as fhandles, Pool() as p:
            sub_functions[0][0] = mp_logger
            queue = p.imap(main_function, aggregated_multipage_articles_gen(warc_filename, sub_functions),
                           chunksize=1000)
            for ret in queue:  # This is single process because it writes to files
                yield after_function(ret, after_params, fhandles)


# This function is used outside of this file
def dummy_fun(*_):
    return None


LOCALE_LOCK = threading_Lock()


@contextmanager
def safe_setlocale(name):
    """
    Set locale in a context for date parsing in a thread-safe manner.
    Original code:
    https://stackoverflow.com/questions/18593661/how-do-i-strftime-a-date-object-in-a-different-locale/24070673#24070673
    """
    with LOCALE_LOCK:
        saved = setlocale(LC_ALL)
        try:
            yield setlocale(LC_ALL, name)
        except locale_Error as e:
            raise e  # Here one can implement a friendly error message
        finally:
            setlocale(LC_ALL, saved)


# This function is used outside of this file
def parse_date(date_raw, date_format, locale='hu_HU.UTF-8'):
    """Parse date according to the parameters (locale and date format)"""
    with safe_setlocale(locale):
        try:
            return datetime.strptime(date_raw, date_format)
        except ValueError:
            return None


def process_article(params):
    """A generic article processing skeleton used by multiple targets.
       It extracts the useful part from the html (=the body of the article), deletes the listed, irrelevant parts,
        and indicates the characteristic errors related to the body of the article (which can be detected at this level)
    """
    article_list, (tei_logger, article_roots, decomp_fun, excluded_tags_fun, sub_fun, sub_fun_params) = params
    for article_url, warc_date, warc_id, raw_html in article_list:
        bs = BeautifulSoup(raw_html, 'lxml')
        for args, kwargs in article_roots:
            article_body_root = bs.find(*args, **kwargs)
            if article_body_root is not None:
                break
        else:  # article_body_root is always None...
            tei_logger.log('ERROR', 'ROOT ERROR:', article_url)
            return
        # Checks if there are too many unicode escaped characters present in the article body
        if unicode_test(article_body_root.text) < 25:
            # Deleting irrelevant subtrees from the article body
            decomp_fun(article_body_root)
            sub_fun(*sub_fun_params, article_url, article_body_root, excluded_tags_fun)

            if len(article_body_root.text.strip()) < 3:  # Article without text
                tei_logger.log('ERROR', 'EMPTY ARTICLE:', article_url)
        else:
            tei_logger.log('ERROR', 'UNICODE error', article_url)


# This function is used outside of this file
def run_main(warc_filename, configs_dir, log_dir, warc_dir, output_dir, init_portal_fun, run_params=None,
             logfile_level='INFO', console_level='INFO'):
    """This is the main function. It reads the input warc-portalname pairs and process them one by one"""

    check_exists(output_dir, check_fun=os_path_isdir, message='Directory not found')

    for warc_name, portal_name in read_input_config(warc_filename):

        # 1. Read portal-specific configuration (initializing the dictionaries based on the received parameters)
        tei_logger, warc_level_params, *rest_config_params = \
            read_portalspec_config(configs_dir, portal_name, warc_dir, warc_name, log_dir, run_params,
                                   logfile_level=logfile_level, console_level=console_level)

        # 2. Initialize variables according to the given task
        accumulator, after_article_fun, after_article_params, log_file_names_and_modes, out_filenames_and_modes,\
            final_fun, process_article_fun, process_article_params, run_fun = \
            init_portal_fun(log_dir, output_dir, run_params, portal_name, tei_logger,
                            warc_level_params, rest_config_params)

        # 3. Process all articles in the WARC file sequentially or parallel (according to run_fun)
        date_max = datetime(MINYEAR, 1, 1)
        date_min = datetime(MAXYEAR, 1, 1)
        for publish_date in run_fun(warc_level_params, log_file_names_and_modes, process_article_fun,
                                    process_article_params, after_article_fun, after_article_params):
            if publish_date is not None:
                date_min = min(date_min, publish_date)
                date_max = max(date_max, publish_date)

        # 4. After all articles are processed summarize the accumulated information (dates, etc.)
        with open_multiple_files(out_filenames_and_modes) as out_files:
            final_fun((date_min, date_max), out_files, accumulator, tei_logger)

        tei_logger.log('INFO', f'{portal_name} PORTAL FINISHED')
