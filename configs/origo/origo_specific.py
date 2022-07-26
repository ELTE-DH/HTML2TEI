#!/usr/bin/env python3
# -*- coding: utf-8, vim: expandtab:ts=4 -*

import re
from bs4 import BeautifulSoup
from os.path import join as os_path_join, dirname as os_path_dirname, abspath as os_path_abspath
from html2tei import parse_date, decompose_listed_subtrees_and_mark_media_descendants, tei_defaultdict, BASIC_LINK_ATTRS

PORTAL_URL_PREFIX = 'https://www.origo.hu/'

ARTICLE_ROOT_PARAMS_SPEC = [(('article',),{'class': 'article-body'}),
                            (('div',),{'class': 'col-xl-8'}),
                            (('div',), {'class': 'swiper-wrapper'}),
                            (('article',), {'id': 'article-center'}),
                            (('article',), {'id': 'article-text'}),
                            (('div',), {'id': 'cikk'}),
                            (('div',), {'class': 'article_text'}),
                            (('div',), {'id': {'kenyer-szov'}})
                           #(('div',), {'class': 'o-section-main'})
                           ]

SUBJ_DICT = {'auto': 'Autó',
             'filmklub': 'Filmklub',
             'gazdasag': 'Gazdaság',
             'itthon': 'Itthon',
             'nagyvilag': 'Nagyvilág',
             'sport': 'Sport',
             'tafelspicc': 'Tafelspicc',
             'techbazis': 'Techbázis',
             'tudomany': 'Tudomány',
             'idojaras': 'Időjárás',
             'jog': 'Jog',
             'palyabea': 'Palya Bea',
             'programajanlo': 'Programajánló',
             'teve': 'Tévé',
             'uzletinegyed': 'Üzletinegyed',
             'amerikai-elnokvalasztas-2008': 'amerikai elnökválasztás 2008',
             'nepszavazas-2008': 'népszavazás 2008'
             }


URL_KEYWORDS = {'allas-karrier': 'állás-karrier',
                'biztositas': 'biztosítás',
                'blog': 'blog',
                'csapat': 'csapat',
                'eb': 'eb',
                'egyeni': 'egyéni',
                'esport': 'esport',
                'feature': 'feature',
                'focieb': 'focieb',
                'futball': 'futball',
                'galeria': 'galéria',
                'hirdetes': 'hirdetés',
                'hirek': 'hírek',
                'kozvetites': 'közvetítés',
                'lakossagi': 'lakossági',
                'laza': 'laza',
                'limit': 'limit',
                'loero': 'lóerő',
                'mupa': 'müpa',
                'nagyhasab': 'nagyhasáb',
                'olimpia': 'olimpia',
                'percrolpercre': 'percrőlpercre',
                'post': 'post',
                'publikaciok': 'publikációk',
                'szotar': 'szótár',
                'tomegsport': 'tömegsport',
                'trashtalk': 'trashtalk',
                'uzleti': 'üzleti',
                'valsag': 'válság',
                'vb': 'vb',
                'vizesvb': 'vizesvb',
                'onkormanyzati-valasztas-2010': 'önkormányzati választás 2010',
                'valasztas2010': 'választás 2010'
                }


NON_AUTHORS = ['', 'MTI']  # Empty string and Sources


def get_meta_from_articles_spec(tei_logger, url, bs):
    
    def _sort_authors(_data, author_tag_list):
        authors = [a.get_text(strip=True) for a in author_tag_list if a.get_text(strip=True) not in NON_AUTHORS]
        sources = [a.get_text(strip=True) for a in author_tag_list if a.get_text(strip=True) in NON_AUTHORS[1:]]
        if len(authors) > 0:
            _data['sch:author'] = authors
        if len(sources) > 0:
            _data['sch:source'] = sources
        return _data

    def _date_from_url(_url):
        date_from_url = re.search(r'(?<=/)\d{8}', _url).group(0)

        if date_from_url is not None:

            parsed_date_from_url = parse_date(str(date_from_url), "%Y%m%d")
            if parsed_date_from_url is not None:
                return parsed_date_from_url
            else:
                tei_logger.log('WARNING', f'{_url} COULD NOT PARSE DATE FROM URL!')
                return None

    def _keywords(data, intext):
        keywords_from_meta = []
        keywords_scripts = [a for a in bs.find_all('script') if 'window.exclusionTags' in a.text]
        if len(keywords_scripts) > 0:
            keywords_script = keywords_scripts[0]
            if keywords_script is not None:
                ks = keywords_script.text
                i1 = ks.find('[')
                i2 = ks.find(']')
                keywords = ks[i1+1:i2].replace("'", '').split(',')
                if len(keywords) > 0:
                    keywords_from_meta = [k.strip() for k in keywords]
        
        # KEYWORDS FROM URL  TODO is this needed?
        # 4 or 5 in URL_KEYWORDS then add to url_keywords
        url_keywords = []
        for k in [4, 5]:
            if len(split_url) >= k+1 and split_url[k] in URL_KEYWORDS:
                url_keywords.append(URL_KEYWORDS[split_url[k]])

        if len(intext) > 0 or len(keywords_from_meta) > 0 or len(url_keywords) > 0:
            data['sch:keywords'] = list(set(intext) | set(keywords_from_meta) | set(url_keywords))
        else:
            tei_logger.log('DEBUG', f'{url} NO KEYWORDS FOUND')
        return data

    def _format1(data):

        # format 1 title
        title = bs.find('h1', class_='article-title')

        if title is not None:
            data['sch:name'] = title.text.strip()
        else:
            tei_logger.log('WARNING', f'{url}: FORMAT 1 TITLE NOT FOUND IN URL!')

        # format 1 author and date published
        article_info = bs.find('div', class_='article-info')
        if article_info is not None:
            
            authors_or_sources = article_info.find_all('span', class_='article-author')
            if len(authors_or_sources) > 0:
                data = _sort_authors(data, authors_or_sources)
            else:
                tei_logger.log('DEBUG', f'{url}: FORMAT 1 AUTHOR TAG NOT FOUND!')

            date_tag = article_info.find('div', class_='article-date')
            if date_tag is not None and 'datetime' in date_tag.attrs.keys():
                parsed_date = parse_date(date_tag.attrs['datetime'], '%Y-%m-%dT%H:%M')
                data['sch:datePublished'] = parsed_date
            elif date_tag.get_text(strip=True) == '':  # sometimes no publish date is provided, only modification date
                data['sch:datePublished'] = None
            else:
                tei_logger.log('DEBUG', f'{url}: FORMAT 1 DATE FORMAT ERROR!')

        else:
            tei_logger.log('WARNING', f'{url}: FORMAT 1 ARTICLE INFO NOT FOUND!')
            
        # format 1 body contents
        article_body = bs.find('div', class_='col-xl-8')
        if article_body is not None:
            # format 1 article section
            section_tag_f1 = bs.find('span', class_='opt-title')
            if section_tag_f1 is not None:
                section = section_tag_f1.get_text(strip=True)
                if len(section) > 0:
                    data['sch:articleSection'] = section
            else:
                tei_logger.log('WARNING', f'{url}: FORMAT 1 ARTICLE SECTION TAG NOT FOUND!')

            # format 1 keywords
            keywords_root = article_body.find('div', class_='article-meta')
            if keywords_root is not None:
                article_tags = [a.text.strip() for a in keywords_root.find_all('a') if a is not None]
                
                if len(article_tags) > 0:
                    intext_keywords = article_tags
                    data = _keywords(data, intext_keywords)
                else:
                    tei_logger.log('DEBUG', f'{url}: FORMAT 1 KEYWORDS NOT FOUND!')
        return data

    def _format2(data):
        article_head_format_2 = bs.find('header', {'id': 'article-head'})

        # format 2 title
        title_tag = article_head_format_2.find('h1')
        if title_tag is not None:
            title = title_tag.get_text(strip=True)
            if len(title) > 0:
                data['sch:name'] = title
        else:
            tei_logger.log('WARNING', f'{url}: FORMAT 2 TITLE NOT FOUND!')

        # format 2 date published and author
        d_and_a_tag = article_head_format_2.find('div', {'class': 'address top'})
        if d_and_a_tag is not None:
            authors_or_sources = d_and_a_tag.find_all('span', {'class': 'article-author'})
            if len(authors_or_sources) > 0:
                data = _sort_authors(data, authors_or_sources)
            else:
                tei_logger.log('DEBUG', f'{url}: FORMAT 2 AUTHOR STRING NOT PRESENT IN TAG!')
                
            date_pub_tag = d_and_a_tag.find('span', {'id': 'article-date', 'pubdate': 'pubdate', 'datetime': True})
            if date_pub_tag is not None:
                pub_date = parse_date(date_pub_tag['datetime'].strip(), '%Y-%m-%dT%H:%M')
                if pub_date is not None:
                    data['sch:datePublished'] = pub_date
                else:
                    tei_logger.log('WARNING', f'{url}: FORMAT 2 FAILED TO PARSE DATE PUBLISHED!')
            else:
                data['sch:datePublished'] = _date_from_url(url)
        else:
            tei_logger.log('WARNING', f'{url}: FORMAT 2 DATE AND AUTHOR TAGS NOT FOUND!')
        return data

    def _format3(data): 
        # format 3 gallery
        gallery_base = bs.find('body', {'class': 'gallery'})  # TODO Is this okay as a base? 
        g_header = gallery_base.find('header')
        if g_header is not None:
            title_tag = g_header.find('h1', {'class': 'gallery-title'})
            if title_tag is not None:
                title = title_tag.get_text(strip=True)
                if len(title) > 0:
                    data['sch:name'] = title
                else:
                    tei_logger.log('WARNING', f'{url}: FORMAT 3 GALLERY ARTICLE TITLE EMPTY!')
            else:
                tei_logger.log('WARNING', f'{url}: FORMAT 3 GALLERY ARTICLE TITLE NOT FOUND!')
        else:
            tei_logger.log('WARNING', f'{url}: FORMAT 3 GALLERY ARTICLE TITLE NOT FOUND!')

        # format 3 publish date
        pub_date_tag = bs.find('meta', {'name': 'publish-date', 'content': True})
        if pub_date_tag is not None:
            pub_date = parse_date(pub_date_tag['content'], '%Y-%m-%d')
            if pub_date is not None:
                data['sch:datePublished'] = pub_date
            else:
                tei_logger.log('WARNING', f'{url} FORMAT 3 FAILED TO PARSE PUBDATE OF GALLERY ARTICLE!')
        else:
            tei_logger.log('WARNING', f'{url} FORMAT 3 PUBDATE NOT FOUND!')

        # 'gallery' is added to keywords
        if '/galeria/' in url:
            intext_keywords = ['galéria']
            data = _keywords(data, intext_keywords)
        else:
            tei_logger.log('WARNING', f'{url} FORMAT 3 GALLERY LINK FAILED TO PARSE')
        # author never present on gallery article
        return data

    def _format4(data):
        # format 4 news feed

        title_tag = bs.find('title')
        if title_tag is not None:
            title = title_tag.get_text(strip=True)
            if len(title) > 0:
                data['sch:name'] = title
        else:
            tei_logger.log('WARNING', f'{url} FORMAT 4 TITLE NOT FOUND!')
        # format 4 publish date
        pub_date_tag = bs.find('meta', {'name': 'publish-date', 'content': True})
        if pub_date_tag is not None:
            pub_date = parse_date(pub_date_tag['content'], '%Y-%m-%d')
            if pub_date is not None:
                data['sch:datePublished'] = pub_date
            else:
                tei_logger.log('WARNING', f'{url} FORMAT 4 PUB DATE FAILED TO PARSE!')
        else:
            tei_logger.log('WARNING', f'{url} FORMAT 4 PUB DATE NOT FOUND!')

        # format 4 keywords taken from url
        if len(split_url) > 4 and (split_url[4] or split_url[5]) == 'kozvetites':
            intext_keywords = ['közvetítés']
            data = _keywords(data, intext_keywords)
        return data

    def _format5(data):
        # format 5 - https://www.origo.hu/itthon/valasztas2010/20100210-ujabb-feltort-levelszekrenyek-utan-nyomoz-a-rendorseg.html
        article_body = bs.find('div', {'id': 'cikk'})
        # format 5 title
        title_tag1 = article_body.find('div', {'class': 'article_head'})
        if title_tag1 is not None:
            title_h1 = title_tag1.find('h1')
            if title_h1 is not None:
                title = title_h1.get_text(strip=True)
                if len(title) > 0:
                    data['sch:name'] = title
                else:
                    tei_logger.log('WARNING', f'{url} FORMAT 5 ARTICLE TITLE TAG EMPTY!')
            else:
                tei_logger.log('WARNING', f'{url} FORMAT 5 ARTICLE TITLE TAG NOT FOUND!')
        else:
            title_tag2 = bs.find('h1', {'class': 'cikk-cim'})
            if title_tag2 is not None:
                title_h12 = title_tag2.get_text(strip=True)
                if title_h12 is not None:
                    data['sch:name'] = title_h12
                else:
                    tei_logger.log('WARNING', f'{url} FORMAT 5 ARTICLE TITLE TAG EMPTY!')
            else:
                tei_logger.log('WARNING', f'{url} FORMAT 5 ARTICLE TITLE NOT FOUND')

        # format 5 author and datePublished span class="cikk-datum">2009. 01. 11., 19:19</span>
        header = article_body.find('div', {'id': 'cikk_fejlec'})
        
        if header is not None:
            authors_tag = header.find('span', {'class': 'author'})
            if authors_tag is not None:
                authors_or_sources = authors_tag.find_all('a')
                data = _sort_authors(data, authors_or_sources)
            else:
                tei_logger.log('DEBUG', f'{url} FORMAT 5 AUTHOR TAG NOT FOUND')
            date_tag = header.find('span', {'class': 'create_date'})
            if date_tag is not None:
                pub_date = date_tag.get_text(strip=True)
                if len(pub_date) > 0:
                    parsed_pub = parse_date(pub_date.replace('Létrehozás dátuma: ', ''), "%Y. %m. %d., %H:%M")
                    if parsed_pub is not None:
                        data['sch:datePublished'] = parsed_pub
                    else:
                        tei_logger.log('WARNING', f'{url} FORMAT 5 PUB DATE FAILED TO PARSE!')
                else:
                    tei_logger.log('WARNING', f'{url} FORMAT 5 PUB DATE EMPTY!')
        else:
            header2 = bs.find('div', {'id': 'cikk'})
            
            if header2 is not None:
                author_tag = header2.find('a', {'class': 'cikk-szerzo'})
                if author_tag is not None:
                    author = author_tag.get_text(strip=True)
                    if author is not None:
                        if author in NON_AUTHORS[1:]:
                            data['sch:source'] = [author]
                        else:    
                            data['sch:author'] = [author]
                date_pub_tag = header2.find('span', {'class':'cikk-datum'})
                if date_pub_tag is not None:
                    pub_date = date_pub_tag.get_text(strip=True)
                    if pub_date is not None:
                        pub_date_parsed = parse_date(pub_date, "%Y. %m. %d., %H:%M")
                        if pub_date_parsed is not None:
                            data['sch:datePublished'] = pub_date_parsed
                    else:
                        tei_logger.log('WARNING', f'{url} FORMAT 5 PUB DATE EMPTY!')        
                else:
                    tei_logger.log('WARNING', f'{url} FORMAT 5 PUB DATE TAG NOT FOUND!')                
            else:
                tei_logger.log('WARNING', f'{url} FORMAT 5 PUB DATE NOT FOUND!')
        return data

    def _format6(data):
        # format 6 palyabea
        palyabea_base = bs.find('body', {'id': '!BODY_ID'})
        # format 6 title
        title_tag = palyabea_base.find('div', {'class': 'title'})
        if title_tag is not None:
            title = title_tag.get_text(strip=True)
            if len(title) > 0:
                data['sch:name'] = title
            else:
                tei_logger.log('DEBUG', f'{url} FORMAT 6 ARTICLE TITLE TAG EMPTY!')
        else:
            tei_logger.log('DEBUG', f'{url} FORMAT 6 ARTICLE TITLE NOT FOUND!')
        # format 6 pubdate
        pubdate_tag = palyabea_base.find('div', {'class': 'date'})
        if pubdate_tag is not None:
            pubdate_span = pubdate_tag.find('span', {'class': False})
            if pubdate_span is not None:
                pubdate = pubdate_span.get_text(strip=True)
                if len(pubdate) > 0:
                    parsed_pub = parse_date(pubdate, "%Y. %B. %d.")
                    if parsed_pub is not None:
                        data['sch:datePublished'] = parsed_pub
                    else:
                        tei_logger.log('WARNING', f'{url} FORMAT 6 PUB DATE FAILED TO PARSE!')
                else:
                    tei_logger.log('WARNING', f'{url} FORMAT 6 PUB DATE TAG EMPTY!')
            else:
                tei_logger.log('WARNING', f'{url} FORMAT 6 PUB DATE TAG NOT FOUND!')
        else:
            format_6_date_from_url = _date_from_url(url)
            if format_6_date_from_url is not None:
                data['sch:datePublished'] = format_6_date_from_url
            else:
                tei_logger.log('WARNING', f'{url} FORMAT 6 PUB DATE COULD NOT BE PARSED FROM URL!')

        # format 6 keywords
        paly_head = palyabea_base.find('div', {'id': 'left'})
        if paly_head is not None:
            paly_tags = paly_head.find_all('a', {'href': True, 'title': True, 'class': False})
            if len(paly_tags) > 0:
                intext_keywords = [t.get_text(strip=True) for t in paly_tags if t.get_text(strip=True) != '']
                data = _keywords(data, intext_keywords)
            else:
                tei_logger.log('DEBUG', f'{url} FORMAT 6 KEYWORD TAGS NOT FOUND!')
        return data

    def _format7(data):
        pub_date_meta_tag = bs.find('meta', {'name': 'publish-date', 'content': True})
        if pub_date_meta_tag is not None:
            parsed_pub_date = parse_date(pub_date_meta_tag['content'], "%Y-%m-%d")
            if parsed_pub_date is not None:
                data['sch:datePublished'] = parsed_pub_date
            else:
                tei_logger.log('WARNING', f'{url} FAILED TO PARSE FORMAT 7 PUBLISH DATE!')
        else:
            format_7_date_from_url = _date_from_url(url)
            if format_7_date_from_url is not None:
                data['sch:datePublished'] = format_7_date_from_url
            else:
                tei_logger.log('WARNING', f'{url} FORMAT 7 PUBBLISH DATE TAG NOT FOUND!')

        mod_date_meta_tag = bs.find('meta', {'name': 'publish-date', 'content': True})
        if mod_date_meta_tag is not None:
            parsed_mod_date = parse_date(mod_date_meta_tag['content'], "%Y-%m-%d")
            if mod_date_meta_tag is not None:
                data['sch:datePublished'] = parsed_mod_date
            else:
                tei_logger.log('DEBUG', f'{url} FAILED TO PARSE FORMAT 7 MODIFICATION DATE!')
        else:
            tei_logger.log('DEBUG', f'{url} FORMAT 7 MODIFICATION DATE TAG NOT FOUND!')
        
        title_tag = bs.find('title')
        if title_tag is not None:
            title_text = title_tag.get_text(strip=True)
            if title_text is not None:
                data['sch:name'] = title_text
            else:
                tei_logger.log('WARNING', f'{url} FORMAT 7 TITLE TAG EMPTY!')
        else:
            tei_logger.log('WARNING', f'{url} FORMAT 7 TITLE TAG NOT FOUND!')
        
        keywords_tag = bs.find('div', {'class': 'article-meta'})
        if keywords_tag is not None:
            keyword_tags = keywords_tag.find_all('a', {'title': True})
            if len(keyword_tags) > 0:
                intext_keywords = [a['title'].strip() for a in keyword_tags]
                data = _keywords(data, intext_keywords)
        
        art_section_tag = bs.find('span', {'class': 'opt-title'})
        if art_section_tag is not None:
            art_section = art_section_tag.get_text(strip=True)
            if art_section is not None:
                data['sch:articleSection'] = art_section
        return data

    def _format8(data):
        """
        Most articles are from the USA 2008 election news column.
        e.g.: https://www.origo.hu/amerikai-elnokvalasztas-2008/20080726-amerikai-
        elnokvalasztas-barack-obama-demokrata-jelolt-kulpolitia-irak-afganisztan.html
        No data is available from the htmls, even the title of the articles are missing.
        """
        data['sch:datePublished'] = _date_from_url(url)
        return data

    data = tei_defaultdict()

    data['sch:url'] = url
    split_url = url.split('/')

    format_dict = {('header', ('class', 'article-head')): _format1,
                   ('header', ('id', 'article-head')): _format2,
                   ('body', ('class', 'gallery')): _format3,
                   ('div', ('class', 'sportonline_header')): _format4,
                   ('div', ('id', 'cikk')): _format5,
                   ('body', ('id', '!BODY_ID')): _format6,
                   ('article', ('class', 'article-body')): _format7,
                   ('div', ('id', 'kenyer-szov')): _format8,
                   }

    format_identified = False
    for c, (key, format_option) in enumerate(format_dict.items()):
        article_root = bs.find(key[0], {key[1][0]: key[1][1]})
        if article_root is not None:            
            # print(c+1)
            data = format_option(data)
            format_identified = True
            break
    if format_identified is False:
        tei_logger.log('WARNING', f'{url} ARTICLE FORMAT UNACCOUNTED FOR!')

    # DATE MODIFIED from META TAG - same in all <meta name="modified-date" content="2022-03-17" />
    date_modified_tag = bs.find('meta', {'name': 'modified-date', 'content': True})
    if date_modified_tag is not None:
        date_modified = parse_date(date_modified_tag['content'], '%Y-%m-%d')
        if date_modified is not None:
            data['sch:dateModified'] = date_modified
        else:
            tei_logger.log('DEBUG', f'{url} DATE MODIFIED FAILED TO PARSE')

    # ARTICLE SECTION FROM LINK
    if data['sch:articleSection'] is None:
        if split_url[3] in SUBJ_DICT.keys():
            data['sch:articleSection'] = SUBJ_DICT[split_url[3]]
        else:
            tei_logger.log('WARNING', f'{url} ARTICLE SECTION UNACCOUNTED FOR IN SUBJ_DICT!')

    if 'sch:datePublished' not in data.keys():
        tei_logger.log('WARNING', f'{url} DATE PUBLISHED UNACCOUNTED FOR!')
    return data


def excluded_tags_spec(tag):

    tag_attrs = tag.attrs

    # if tag.name == 'iframe' and all(x in ''.join(tag.attrs.keys()) for x in ['width', 'height', 'src', 'allowfullscreen', 'webkitallowfullscreen', 'mozallowfullscreen', 'frameborder']) is True:
    #     print(tag)

    if tag.name == 'td' and 'title' in tag_attrs.keys():
        tag['title'] = '@TITLE'

    if tag.name == 'text' and 'y' in tag_attrs.keys():
        tag['y'] = '@NUM'

    if tag.name == 'a' and 'id' in tag_attrs.keys():
        tag['id'] = '@ID'

    if tag.name == 'a' and 'name' in tag_attrs.keys():
        tag['name'] = '@NAME'

    if tag.name == 'a' and 'data-iframely-url' in tag_attrs.keys():
        tag['data-iframely-url'] = '@DATA-IFRAMELY-URL'

    if tag.name == 'area' and 'alt' in tag_attrs.keys() and 'coords' in tag_attrs.keys():
        tag['alt'] = '@ALT'
        tag['coords'] = '@LONG'

    if tag.name == 'input' and 'name' in tag_attrs.keys() and 'id' in tag_attrs.keys():
        tag['name'] = '@NAME'
        tag['id'] = '@ID'

    if tag.name == 'param' and 'name' in tag_attrs.keys() and 'value' in tag_attrs.keys():
        tag['name'] = '@NAME'
        tag['value'] = '@VALUE'

    if tag.name == 'div' and 'data-lastmodifieddate' in tag_attrs.keys():
        tag_attrs['data-lastmodifieddate'] = '@DATE'

    if tag.name == 'div' and 'data-date' in tag_attrs.keys():
        tag_attrs['data-date'] = '@DATE'

    if tag.name == 'div' and 'data-time' in tag_attrs.keys():
        tag_attrs['data-time'] = '@DATE'

    if tag.name == 'text' and 'x' in tag_attrs.keys():
        tag_attrs['x'] = '@NUM'

    if tag.name == 'link' and 'text' in tag_attrs.keys():
        tag_attrs['text'] = '@LONG'

    if tag.name == 'rect' and 'x' in tag_attrs.keys():
        tag_attrs['x'] = '@NUM'
        
    if tag.name == 'rect' and 'y' in tag_attrs.keys():
        tag_attrs['y'] = '@NUM'

    return tag


BLOCK_RULES_SPEC = {}
BIGRAM_RULES_SPEC = {}
LINKS_SPEC = BASIC_LINK_ATTRS
DECOMP = [(('div',), {'id': 'lablec'}),
          (('div',), {'class': 'aside-content'}),
          (('div',), {'class': 'dinamic-related', 'id': 'related-articles'}),
          ]

MEDIA_LIST = []


def decompose_spec(article_dec):
    decompose_listed_subtrees_and_mark_media_descendants(article_dec, DECOMP, MEDIA_LIST)
    # Getting rid of embedded origo.hu articles
    for c in article_dec.find_all('div', {'class': 'iframely-embed'}):
        att_tag = c.find('a', {'href': True})
        if att_tag is not None and 'https://www.origo.hu/' in att_tag['href']:
            c.decompose()
    return article_dec


BLACKLIST_SPEC = [url.strip() for url in open(os_path_join(os_path_dirname(os_path_abspath(__file__)),
                                                           'origo_BLACKLIST.txt')).readlines()] \
                + [url.strip() for url in open(os_path_join(os_path_dirname(os_path_abspath(__file__)),
                                                            'content_not_available_at_crawl.txt')).readlines()]
# TODO content_not_available_at_crawl.txt

# http://:www.origo.hu/nagyvilag/20110402-radioaktiv-viz-omlik-a-tengerbe-japanban.html

bad_url_list = [url.strip() for url in open(os_path_join(os_path_dirname(os_path_abspath(__file__)),
                                            'bad_reference_urls.txt')).readlines()] \
                + ['&lt;iframe', '&lt;blockquote']
                
LINK_FILTER_SUBSTRINGS_SPEC = re.compile('|'.join([re.escape(s) for s in bad_url_list]))

MULTIPAGE_URL_END = re.compile(r'.*\?pIdx=[0-9]*')


def next_page_of_article_spec(curr_html):
    bs = BeautifulSoup(curr_html, 'lxml')
    pages = bs.find('a', {'class': 'ap-next', 'rel': 'next', 'href': True})
    if pages:
        link = pages['href']
        link = f'https://www.origo.hu{link}'
        return link
    return None
