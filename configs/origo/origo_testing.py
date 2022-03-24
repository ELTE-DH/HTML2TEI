import re
import json
import locale
import requests
from mplogger import Logger
from datetime import datetime
from bs4 import BeautifulSoup
from collections import Counter
from html2tei import parse_date

from warcio.archiveiterator import ArchiveIterator
from webarticlecurator import WarcCachingDownloader

from origo_specific import get_meta_from_articles_spec as get_meta


def response_warc_record_gen(warc_filename):
    archive_base = ArchiveIterator(open(warc_filename, 'rb'))
    for rec in archive_base:
        if rec.rec_type == 'response':
            article_url = rec.rec_headers.get_header('WARC-Target-URI')
            raw_html = rec.content_stream().read()
            yield article_url, raw_html


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


logger = Logger()
warc_file = '../../warcs_dir/origo-articles_new3.warc.gz'

origo_iterator = response_warc_record_gen(warc_file)

json_dict = {}
for i in range(729885):
    url, html = next(origo_iterator)
    bs = BeautifulSoup(html, 'lxml')
    json_dict[url] = get_meta(logger, url, bs)

with open('/home/dh/PycharmProjects/HTML2TEI/configs/origo/origo_meta.json', 'w') as json_file:
    json.dump(json_dict, json_file, ignore_ascii=True)
