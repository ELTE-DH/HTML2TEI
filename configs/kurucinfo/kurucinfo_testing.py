import requests
from datetime import datetime

from html2tei import parse_date
from warcio.archiveiterator import ArchiveIterator
from webarticlecurator import WarcCachingDownloader
from bs4 import BeautifulSoup
from mplogger import Logger
import json

from os import path
from html2tei import parse_date
from kurucinfo_specific import get_meta_from_articles_spec, ARTICLE_ROOT_PARAMS_SPEC, DECOMP


def safe_extract_hrefs_from_a_tags(main_container):
    """
    Helper function to extract href from a tags
    :param main_container: An iterator over Tag()-s
    :return: Generator over the extracted links
    """
    for a_tag in main_container:
        a_tag_a = a_tag.find('a')
        if a_tag_a is not None and 'href' in a_tag_a.attrs:
            yield a_tag_a['href']

def experiment1():
    with open('table_errors_magyarnarancs.txt', 'w') as file:
        iterator = response_warc_record_gen(warc_filename)
        for count, i in enumerate(range(89114)):
            url, html = next(iterator)
            soup = BeautifulSoup(html, 'lxml')

            if count % 100 == 0:
                print(f'{round((count / 89114) * 100, 2)} %')
            for table in  soup.find_all('table'):
                img = table.find('img')
                if len(table.text.strip()) > 0 and img is not None:
                    print(f'BOTH TEXT AND IMG: {url}', file=file)

def extract_article_urls_from_page_kurucinfo(archive_page_raw_html):
    """
        extracts and returns as a list the URLs belonging to articles from an HTML code
    :param archive_page_raw_html: archive page containing list of articles with their URLs
    :return: list that contains URLs
    """
    soup = BeautifulSoup(archive_page_raw_html, 'lxml')
    main_container = soup.find_all('div', class_='alcikkheader')
    urls = {f'https://kuruc.info{link}' for link in safe_extract_hrefs_from_a_tags(main_container)}
    return urls


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

def response_warc_record_gen(warc_filename):
    archive_base = ArchiveIterator(open(warc_filename, 'rb'))
    for rec in archive_base:
        if rec.rec_type == 'response':
            article_url = rec.rec_headers.get_header('WARC-Target-URI')
            raw_html = rec.content_stream().read()
            yield article_url, raw_html


class TeiLoggerSubstitute:

    def log(self, message):
        pass
        # print(message)


def read_warc(warc_reader):

    for count, url in enumerate(warc_reader.url_index):
        _, _, resp = warc_reader.get_records(url)  # From WebArticleCurator
        warc_response_datetime, warc_id, raw_html = extract_resp_record_data(resp)
        yield warc_response_datetime, warc_id, raw_html, url


def run_test(link):
    soup = BeautifulSoup(requests.get(link).text, 'lxml-xml')
    print(get_meta_from_articles_spec(TeiLoggerSubstitute, link, soup))


def find_root(link, spec):
    soup = BeautifulSoup(requests.get(link).text, 'lxml-xml')
    print(soup.find(spec[0][0][0], spec[0][1]))


def find_decomp(link, D):
    soup = BeautifulSoup(requests.get(link).text, 'lxml-xml')

    for decomp in D:
        number_of_finds = len(soup.find_all(decomp[0][0], decomp[1]))
        print(number_of_finds, '---', decomp)


warc_filename = '../../warcs_dir/kurucinfo-articles_new9.warc.gz'
# w = WarcCachingDownloader(warc_filename, None, TeiLoggerSubstitute, just_cache=True, download_params={'stay_offline': True})
# 233796

def write_authors():
    archive_iter = ArchiveIterator(open(warc_filename, 'rb'))

    with open('kuruc_meta1.tsv', 'w') as file:
        for i in range(233796):
            if i % 100 == 0:
                print(f'{round((i / 233796) * 100, 2)} %')
            url, html = next(response_warc_record_gen(archive_iter))
            md = get_meta_from_articles_spec(TeiLoggerSubstitute, url, BeautifulSoup(html, 'lxml'))
            print(f"{md['sch:url']}\t{md['sch:name']}\t{md['sch:author']}\t{md['sch:datePublished']}\t{md['sch:keywords']}\t{md['sch:articleSection']}", file=file)


def write_authors_publi():
    archive_iter = ArchiveIterator(open(warc_filename, 'rb'))
    with open('kuruc_meta1.tsv', 'w') as file:
        for i in range(233796):
            if i % 100 == 0:
                print(f'{round((i / 233796) * 100, 2)} %')

            url, html = next(response_warc_record_gen(archive_iter))
            bs = BeautifulSoup(html, 'lxml')
            if url.split('/')[4] == '7':
                #################
                article_root = bs.find('div', {'class': 'tblot'})
                if article_root is not None:
                    all_paragraphs = article_root.find_all('div', {'class': 'cikktext', 'id':None})
        
                    if len(all_paragraphs) > 0:
                        possible_author_tag = all_paragraphs[-1]
                        if len(possible_author_tag.get_text(strip=True)) <= 50 and '-' in possible_author_tag.get_text(strip=True):
                            print(f"{possible_author_tag.get_text(strip=True)},{url}", file=file)

def log_time(logger, count, total):
    if count % 100 == 0:
        logger.log('INFO', count, '/', total, '=', round((count / total) * 100, 2), '%')
    


def wirte_meta_json():
    logger = Logger()
    w_filename = '../../warcs_dir/kurucinfo-articles_new13.warc.gz'
    w = WarcCachingDownloader(warc_filename, None, logger, just_cache=True, download_params={'stay_offline': True})

    kuruc_iterator = response_warc_record_gen(w_filename)
    
    for i in range(len(w.url_index)):
        if path.isfile('kuruc_meta_table.json') is False:
            listObj = []
        else:
            with open('kuruc_meta_table.json', 'r') as jsonload:
                listObj = json.load(jsonload)
        log_time(logger, i, len(w.url_index))
        
        url, raw_html = next(kuruc_iterator)
        soup = BeautifulSoup(raw_html, 'lxml')

        kuruc_article_dict = get_meta_from_articles_spec(logger, url, soup)

        if 'sch:datePublished' in kuruc_article_dict.keys():
            kuruc_article_dict['sch:datePublished'] = kuruc_article_dict['sch:datePublished'].isoformat()

        if i % 1000 == 0:
            logger.log('INFO', f'{kuruc_article_dict.keys()}')

        listObj.append(kuruc_article_dict)

        with open('kuruc_meta_table.json', 'w') as json_file:
            json.dump(listObj, json_file, ensure_ascii=False)
    
wirte_meta_json()