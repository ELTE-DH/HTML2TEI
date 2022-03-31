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


def normal_meta():
    json_dict = {}
    for i in range(729885):

        url, html = next(origo_iterator)
        bs = BeautifulSoup(html, 'lxml')
        json_dict[url] = get_meta(logger, url, bs)
        json_dict[url]['sch:datePublished'] = str(json_dict[url]['sch:datePublished'])
        json_dict[url]['sch:dateModified'] = str(json_dict[url]['sch:dateModified'])

        if i == 100:
            with open('/home/dh/PycharmProjects/HTML2TEI/configs/origo/origo_meta.json', 'w') as json_file:
                json.dump(json_dict, json_file, ensure_ascii=False)

        elif i > 100 and i % 100 == 0:
            print(f'{round((i / 729885) * 100, 2)}%')

            with open('/home/dh/PycharmProjects/HTML2TEI/configs/origo/origo_meta.json', 'r') as json_file:
                in_dict = json.load(json_file)
                joint_dict = {**in_dict, **json_dict}
            with open('/home/dh/PycharmProjects/HTML2TEI/configs/origo/origo_meta.json', 'w') as json_file:
                json.dump(joint_dict, json_file, ensure_ascii=False)
            json_dict = {}


def just_gallery():
    with open('/home/dh/PycharmProjects/HTML2TEI/configs/origo/gallery_links.txt', 'w') as writefile:
        for i in range(729885):
            if i % 100 == 0:
                print(f'{round((i / 729885) * 100, 2)}%')
            url, html = next(origo_iterator)
            bs = BeautifulSoup(html, 'lxml')

            if bs.find('body', {'class': 'gallery'}) is not None:
                print(url, file=writefile)


def from_request(link):
    txt = requests.get(link).text
    soup = BeautifulSoup(txt, 'lxml')
    return soup

kozvetites_link = 'https://www.origo.hu/sport/kozvetites/20211202-kezilabda-noi-vilagbajnoksag-magyarorszag-szlovakia-elo-kozvetites.html'
olimpia_link = 'https://www.origo.hu/sport/olimpia/galeria/20210726-gordeszka-latvanyos-kepek.html'
#print(get_meta(logger, kozvetites_link, from_request(kozvetites_link)))

normal_meta()