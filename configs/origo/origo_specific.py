#!/usr/bin/env python3
# -*- coding: utf-8, vim: expandtab:ts=4 -*

import re
from os.path import join as os_path_join, dirname as os_path_dirname, abspath as os_path_abspath
from html2tei import parse_date, decompose_listed_subtrees_and_mark_media_descendants, tei_defaultdict, BASIC_LINK_ATTRS

PORTAL_URL_PREFIX = 'https://www.origo.hu/'

ARTICLE_ROOT_PARAMS_SPEC = [(('div',),{'class': 'col-xl-8'}),
                            (('div',), {'class': 'swiper-wrapper'}),
                            (('article',), {'id': 'article-center'})
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
    
    def _sort_authors(data, author_tag_list):
        authors = [a.get_text(strip=True) for a in author_tag_list if a.get_text(strip=True) not in NON_AUTHORS]
        sources = [a.get_text(strip=True) for a in author_tag_list if a.get_text(strip=True) in NON_AUTHORS[1:]]
        if len(authors) > 0:
            data['sch:author'] = authors
        if len(sources) > 0:
            data['sch:source'] = sources    
    
    data = tei_defaultdict()
    data['sch:url'] = url

    intext_keywords = []  # defined in case no keywords are found from text
    article_section = None  # defined in case no article section tags are found

    article_head_format_1 = bs.find('header', class_='article-head')
    if article_head_format_1 is not None: # format 1

        print('\nFORMAT 1')
        # format 1 title
        title = article_head_format_1.find('h1', class_='article-title')

        if title is not None:
            data['sch:name'] = title.text.strip()
        else:
            tei_logger.log('WARNING', f'{url}: TITLE NOT FOUND IN URL!')
        # format 1 author and date published
        article_info = bs.find('div', class_='article-info')
        if article_info is not None:
            
            authors_or_sources = article_info.find_all('span', class_='article-author')
            if len(authors_or_sources) > 0:
                _sort_authors(data, authors_or_sources)
            else:
                tei_logger.log('WARNING', f'{url}: AUTHOR TAG NOT FOUND!')

            date_tag = article_info.find('div', class_='article-date')
            if date_tag is not None and 'datetime' in date_tag.attrs.keys():
                parsed_date = parse_date(date_tag.attrs['datetime'], '%Y-%m-%dT%H:%M')
                data['sch:datePublished'] = parsed_date
            else:
                tei_logger.log('WARNING', f'{url}: DATE FORMAT ERROR!')

        else:
            tei_logger.log('WARNING', f'{url}: ARTICLE INFO NOT FOUND!')
        # format 1 body contents
        article_body = bs.find('div', class_='col-xl-8')
        if article_body is not None:
            # format 1 article section
            section_tag_f1 = article_body.find('a', class_='category-meta')
            if section_tag_f1 is not None:
                section = section_tag_f1.get_text(strip=True)
                if len(section) > 0:
                    article_section = section
            else:
                tei_logger.log('WARNING', f'{url}: FORMAT 1 ARTICLE SECTION TAG NOT FOUND!')
            # format 1 keywords
            keywords_root = article_body.find('div', class_='article-meta')
            if keywords_root is not None:
                article_tags = [a.text.strip() for a in keywords_root.find_all('a') if a is not None]
                # article_tags = article_tags[1:]
                if len(article_tags) > 0:
                    intext_keywords = article_tags
                else:
                    tei_logger.log('DEBUG', f'{url}: KEYWORDS NOT FOUND!')

    else:  # format 2

        article_head_format_2 = bs.find('header', {'id': 'article-head'})
        if article_head_format_2 is not None:
            print('\nFORMAT 2')
            # format 2 title
            title_tag = article_head_format_2.find('h1')
            if title_tag is not None:
                title = title_tag.get_text(strip=True)
                if len(title) > 0:
                    data['sch:name'] = title
            else:
                tei_logger.log('WARNING', f'{url}: TITLE NOT FOUND IN URL!')
            # format 2 date published and author
            d_and_a_tag = article_head_format_2.find('div', {'class': 'address top'})
            if d_and_a_tag is not None:
                author_tags = d_and_a_tag.find_all('span', {'class': 'article-author'})
                if len(author_tags) > 0:
                    authors = [a.get_text(strip=True) for a in author_tags if a.get_text(strip=True) not in NON_AUTHORS]
                    sources = [a.get_text(strip=True) for a in author_tags if a.get_text(strip=True) in NON_AUTHORS[1:]]
                    if len(authors) > 0:
                        data['sch:authors'] = authors
                    if len(sources) > 0:
                        data['sch:source'] = sources
                    else:
                        tei_logger.log('WARNING', f'{url}: AUTHOR STRING NOT PRESENT IN TAG!')
                date_pub_tag = d_and_a_tag.find('span', {'id': 'article-date', 'pubdate': 'pubdate', 'datetime': True})
                if date_pub_tag is not None:
                    pub_date = parse_date(date_pub_tag['datetime'].strip(), '%Y-%m-%dT%H:%M')
                    if pub_date is not None:
                        data['sch:datePublished'] = pub_date
                    else:
                        tei_logger.log('WARNING', f'{url}: FAILED TO PARSE DATE PUBLISHED!')
                else:
                    tei_logger.log('WARNING', f'{url}: DATE AUTHOR NOT FOUND!')
            else:
                tei_logger.log('WARNING', f'{url}: DATE AND AUTHOR NOT FOUND!')

        else:  # format 3 gallery

            gallery_base = bs.find('body', {'class': 'gallery'})
            if gallery_base is not None:
                print('\nFORMAT 3')
                g_header = gallery_base.find('header')
                if g_header is not None:
                    title_tag = g_header.find('h1', {'class': 'gallery-title'})
                    if title_tag is not None:
                        title = title_tag.get_text(strip=True)
                        if len(title) > 0:
                            data['sch:name'] = title
                        else:
                            tei_logger.log('WARNING', f'{url}: GALLERY ARTICLE TITLE NOT FOUND!')

                # format 3 publish date
                pub_date_tag = bs.find('meta', {'name': 'publish-date', 'content': True})
                if pub_date_tag is not None:
                    pub_date = parse_date(pub_date_tag['content'], '%Y-%m-%d')
                    if pub_date is not None:
                        data['sch:datePublished'] = pub_date
                    else:
                        tei_logger.log('WARNING', f'{url} FAILED TO PARSE PUBDATE OF GALLERY ARTICLE')
                split_url = url.split('/')
                # There are no keywords in gallery articles - 'gallery' is added to keywords
                if split_url[4] == 'galeria':
                    intext_keywords = ['galéria']
                elif split_url[4] == 'olimpia' and split_url[5] == 'galeria':
                    intext_keywords = ['olimpia', 'galéria']
                elif split_url[5] == 'galeria':
                    intext_keywords = ['galéria']
                else:
                    tei_logger.log('WARNING', f'{url} GALLERY LINK FAILED TO PARSE')

                # author never present on gallery article

            else:  # format 4 közvetítés
                
                sports_feed_header = bs.find('div', class_='sportonline_header')
                if sports_feed_header is not None:
                    print('\nFORMAT 4')
                    # TODO write sports feed format
                    title_tag = bs.find('title')
                    if title_tag is not None:
                        title = title_tag.get_text(strip=True)
                        if len(title) > 0:
                            data['sch:name'] = title
                    # format 4 publish date
                    pub_date_tag = bs.find('meta', {'name': 'publish-date', 'content': True})
                    if pub_date_tag is not None:
                        pub_date = parse_date(pub_date_tag['content'], '%Y-%m-%d')
                        if pub_date is not None:
                            data['sch:datePublished'] = pub_date
                        else:
                            tei_logger.log('WARNING', f'{url} FAILED TO PARSE PUBDATE OF GALLERY ARTICLE')

                    # format 4 keywords taken from url
                    if split_url[4] == 'kozvetites':
                        intext_keywords = ['közvetítés']
                    elif split_url[4] == 'olimpia' and split_url[5] == 'kozvetites':
                        intext_keywords = ['olimpia', 'közvetítés']
                    elif split_url[4] == 'focieb' and split_url[5] == 'kozvetites':
                        intext_keywords = ['focieb', 'közvetítés']

                else:  # if neither format 1 or 2 or 3 are recognized
                    # format 5 - https://www.origo.hu/itthon/valasztas2010/20100210-ujabb-feltort-levelszekrenyek-utan-nyomoz-a-rendorseg.html
                    article_body = bs.find('div', {'id': 'cikk'})
                    if article_body is not None:
                        print('\nFORMAT 4')
                        # format 5 title
                        title_tag = article_body.find('div', {'class': 'article_head'})
                        if title_tag is not None:
                            title_h1 = title_tag.find('h1')
                            if title_h1 is not None:
                                title = title_h1.get_text(strip=True)
                                if len(title) > 0:
                                    data['sch:name'] = title
                                else:
                                    tei_logger.log('WARNING', f'{url} ARTICLE TITLE NOT FOUND')
                        # format 5 author and datePublished
                        header = article_body.find('div', {'id': 'cikk_fejlec'})
                        if header is not None:
                            authors_tag = header.find('span', {'class': 'author'})
                            if authors_tag is not None:
                                authors_or_sources = authors_tag.find_all('a')
                                _sort_authors(data, authors_or_sources)
                            date_tag = header.find('span', {'class': 'create_date'})
                            if date_tag is not None:
                                pub_date = date_tag.get_text(strip=True)
                                if len(pub_date) > 0:
                                    parsed_pub = parse_date(pub_date.replace('Létrehozás dátuma: ', ''), "%Y. %m. %d., %H:%M")
                                    if parsed_pub is not None:
                                        data['sch:datePublished'] = parsed_pub

                    else:
                        tei_logger.log('WARNING', f'{url} ARTICLE FORMAT UNACCOUNTED FOR')

    # DATE MODIFIED from META TAG - same in all <meta name="modified-date" content="2022-03-17" />
    date_modified_tag = bs.find('meta', {'name': 'modified-date', 'content': True})
    if date_modified_tag is not None:
        date_modified = parse_date(date_modified_tag['content'], '%Y-%m-%d')
        if date_modified is not None:
            data['sch:dateModified'] = date_modified
        else:
            tei_logger.log('WARNING', f'{url} DATE MODIFIED FAILED TO PARSE')

    # KEYWORDS from SCRIPT TAG
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
                keywords_from_meta = keywords
    
    # KEYWORDS FROM URL
    # 4 or 5 in URL_KEYWORDS then add to url_keywords
    split_url = url.split('/')
    url_keywords = []
    for k in [4, 5]:
        if split_url[k] in URL_KEYWORDS:
            url_keywords.append(URL_KEYWORDS[split_url[k]])

    if len(intext_keywords) > 0 or len(keywords_from_meta) > 0 or len(url_keywords) > 0:
        data['sch:keywords'] = list(set(intext_keywords) | set(keywords_from_meta) | set(url_keywords))
    else:
        tei_logger.log('WARNING', f'{url} NO KEYWORDS FOUND')

    # ARTICLE SECTION FROM LINK
    if article_section is None:
        if split_url[3] in SUBJ_DICT.keys():
            data['sch:articleSection'] = SUBJ_DICT[split_url[3]]
        else:
            tei_logger.log('WARNING', f'{url} NEWSFEED ARTICLE SECTION UNACCOUNTED FOR')
    else:
        data['sch:articleSection'] = article_section


    return data


def excluded_tags_spec(tag):
    return tag


BLOCK_RULES_SPEC = {}
BIGRAM_RULES_SPEC = {}
LINKS_SPEC = BASIC_LINK_ATTRS
DECOMP = []
MEDIA_LIST = []


def decompose_spec(article_dec):
    decompose_listed_subtrees_and_mark_media_descendants(article_dec, DECOMP, MEDIA_LIST)
    return article_dec


BLACKLIST_SPEC = [url.strip() for url in open(os_path_join(os_path_dirname(os_path_abspath(__file__)),
                                                           'origo_BLACKLIST.txt')).readlines()]
LINK_FILTER_SUBSTRINGS_SPEC = re.compile('|'.join(['LINK_FILTER_DUMMY_STRING']))

MULTIPAGE_URL_END = re.compile(r'^\b$')  # Dummy


def next_page_of_article_spec(_):
    return None
