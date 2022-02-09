#!/usr/bin/env python3
# -*- coding: utf-8, vim: expandtab:ts=4 -*

import re
from os.path import join as os_path_join, dirname as os_path_dirname, abspath as os_path_abspath
from html2tei import parse_date, BASIC_LINK_ATTRS, decompose_listed_subtrees_and_mark_media_descendants, tei_defaultdict

PORTAL_URL_PREFIX = 'https://alfahir.hu'

_only_video_class = 'field field-name-field-video-hozzaadasa'
_paragraphs_class = 'field field--name-field-paragraphs field--type-entity-reference-revisions ' \
                    'field--label-hidden field--items'
_newsfeed_class = 'percrol-percre node node--type-article node--view-mode-full ds-1col clearfix'
_article_content_class = 'article-content'

ARTICLE_ROOT_PARAMS_SPEC = [(('div',), {'class': _only_video_class}),
                            (('div',), {'class': _paragraphs_class}),
                            (('div',), {'class': _newsfeed_class}),
                            (('div',), {'class': _article_content_class})
                            ]

HTML_BASICS = {'p', 'h2', 'h3', 'h4', 'h5', 'em', 'i', 'b', 'strong', 'mark', 'u', 'sub', 'sup', 'del', 'strike',
               'ul', 'ol', 'li', 'table', 'tr', 'td', 'th', 'quote', 'figure', 'iframe', 'script', 'noscript'}

# List of source formats with over 2 occurences in alfahir-articles_new2.warc.gz
SOURCE_LIST = ['Alfahír', 'police.hu', 'Index.hu', '444.hu', 'BBC', 'mti - barikad.hu', 'MTI', 'police.hu - alfahir.hu',
               'N1TV', 'MTI nyomán alfahir.hu', 'nol.hu - alfahir.hu', 'Index - alfahir.hu', 'blikk.hu - alfahir.hu',
               'MTI nyomán – barikad.hu', 'MTI nyomán - barikad.hu', 'police.hu – alfahir.hu', 'index.hu - alfahir.hu',
               'borsonline.hu – alfahir.hu', 'Nol.hu nyomán - alfahir.hu', 'MTI – alfahir.hu', 'MTI - alfahir.hu',
               'alfahir.hu', 'OB', 'Index.hu nyomán - alfahir.hu', 'MTI nyomán – alfahir.hu', 'blikk.hu – alfahir.hu',
               'MTI nyomán', 'Bors - alfahir.hu', 'Blikk - barikad.hu', 'N1tv - alfahir.hu', 'Blikk – barikad.hu',
               'hvg.hu – alfahir.hu', 'barikad.hu', '24.hu', 'mti – barikad.hu', 'Blikk - alfahir.hu',
               'N1TV - alfahir.hu', 'MTI - barikad.hu', 'MTI nyomán - alfahir.hu', 'MTI – barikad.hu',
               'hvg.hu - barikad.hu', 'MTI, Népszabadság'
               ]


def get_meta_from_articles_spec(tei_logger, url, bs):
    data = tei_defaultdict()
    data['sch:url'] = url

    # Created a list of possible root find patterns to iterate through
    content_root_patterns = [('div', {'class': 'article-content-elements'}),  # basic_article_root
                             ('div', {'class': 'field field-name-field-video-hozzaadasa'}),  # video_root
                             ('div', {'class': 'riport-content'}),  # riport_root
                             ('div', {'class': 'views-infinite-scroll-content-wrapper clearfix form-group'}),  # newsfee
                             ('div', {'class': ['view-minute-by-minute-event-list']}),  # event_list
                             ('div', {'class': 'field field-name-field-image'})  # slideshow
                             ]

    root_found = False  # Might be bad design, added for root not found logging at the end

    # if iteration finds root, it runs and breaks iteration
    for root_pattern in content_root_patterns:
        article_root = bs.find(root_pattern[0], root_pattern[1])
        if article_root is not None and root_pattern != ('form', {'id': 'age-verification-form'}):

            root_found = True

            # Newsfeed format
            percrol_root = bs.find('div', class_='group-right')

            if percrol_root is not None:
                # see: https://alfahir.hu/2021/09/29/ellenzeki_elovalasztas_ellenzeki_
                # partok_dobrev_klara_karacsony_gergely_markizay_peter?page=13

                # AUTHORS - newsfeed has several authors
                author_info_divs = bs.find_all('div', class_='group-left')
                if len(author_info_divs) > 0:
                    auth_tags = []
                    for author_div in author_info_divs:
                        author_name_tag = author_div.find('h4')
                        if author_name_tag is not None:
                            auth_tags.append(author_name_tag)
                    author_list = [au.get_text(strip=True) for au in auth_tags if au.get_text(strip=True) is not None]
                    if len(author_list) > 0:
                        data['sch:author'] = set(author_list)
                    else:
                        tei_logger.log('DEBUG', f'{url}: NEWSFEED AUTHOR TAGS NOT FOUND!')
                else:
                    tei_logger.log('DEBUG', f'{url}: NEWSFEED AUTHOR TAGS NOT FOUND!')

                # DATES - newsfeed dates are calculated according to min and max post times
                all_post_dates = bs.find_all('div', {'class': 'field field-name-field-time'})
                parsed_dates = []
                if len(all_post_dates) > 0:
                    for tag in all_post_dates:
                        time_tag = tag.find('time')
                        if time_tag is not None and 'datetime' in time_tag.attrs.keys():
                            print(time_tag['datetime'])
                            parsed_dates.append(parse_date(time_tag['datetime'], '%Y-%m-%dT%H:%M:%SZ'))
                else:
                    tei_logger.log('WARNING', f'{url}: NEWSFEED POST TIMES NOT FOUND!')
                if len(parsed_dates) > 0:
                    data['sch:datePublished'] = min(parsed_dates)
                    data['sch:dateModified'] = max(parsed_dates)

            # DATES - Non newsfeed dates are handled normally
            if percrol_root is None:
                # DATE MODIFIED - did not add logging as most articles do not have modification date
                date_modified_tag = bs.find('div', {'class': 'field field-name-field-frissitve'})
                if date_modified_tag is not None:
                    date_text = date_modified_tag.get_text(strip=True)
                    if date_text is not None:
                        parsed_data = parse_date(date_text.replace(' |', '').replace('Frissítve', ''), '%Y. %B %d. %H:%M')
                        if parsed_data is not None:
                            data['sch:dateModified'] = parsed_data
                        else:
                            tei_logger.log('WARNING', f'{url}: DATE MODIFIED FORMAT ERROR FAILED TO PARSE!')

                # DATE PUBLISHED
                date_tag = bs.find('div', class_='field field--name-node-post-date '
                                                 'field--type-ds field--label-hidden field--item')
                if date_tag is not None:
                    date_text = date_tag.get_text(strip=True)
                    if date_text is not None:
                        data['sch:datePublished'] = parse_date(date_text.replace(' |', ''), '%Y. %B %d. %H:%M')
                    else:
                        tei_logger.log('WARNING', f'{url}: DATE FORMAT ERROR!')
                else:
                    tei_logger.log('WARNING', f'{url}: DATE TAG NOT FOUND!')

            # AUTHOR and TITLE
            if root_pattern == ('div', {'class': 'riport-content'}):  # riport_root reports have different author tags

                # riport author
                author_roots = bs.find_all('div', {'class': 'field field-name-username'})
                if len(author_roots) > 0:
                    author_tags = [author_root.find('a') for author_root in author_roots]
                    authors = [a.get_text(strip=True) for a in author_tags if a.get_text(strip=True) is not None]
                    if len(authors) > 0:
                        data['sch:author'] = authors
                    else:
                        tei_logger.log('WARNING', f'{url}: AUTHOR TAG EMPTY!')
                else:
                    tei_logger.log('DEBUG', f'{url}: AUTHOR TAG NOT FOUND!')

                # riport title
                title_root = bs.find('div', {'class': 'field field-name-node-title'})
                if title_root is not None:
                    title_tag = title_root.find('h1')
                    if title_tag is not None:
                        title_text = title_tag.get_text(strip=True)
                        if title_text is not None:
                            data['sch:name'] = title_text
                        else:
                            tei_logger.log('WARNING', f'{url}: TITLE TEXT NOT FOUND!')
                    else:
                        tei_logger.log('WARNING', f'{url}: TITLE TAG NOT FOUND!')
                else:
                    tei_logger.log('WARNING', f'{url}: TITLE ROOT NOT FOUND!')

            else:
                # rest author
                author_root = bs.find('div', class_='field--name-field-authors')
                if author_root is not None:
                    author_list = [t.get_text(strip=True) for t in author_root.find_all('h4')
                                   if t.get_text(strip=True) is not None]
                    if len(author_list) > 0:
                        data['sch:author'] = author_list
                    else:
                        tei_logger.log('WARNING', f'{url}: AUTHOR TAG EMPTY!')
                else:
                    tei_logger.log('DEBUG', f'{url}: AUTHOR TAG NOT FOUND!')

                # rest title
                title = bs.find('h1', class_='page-title')
                if title is not None:
                    title_text = title.get_text(strip=True)
                    if title_text is not None:
                        data['sch:name'] = title_text
                    else:
                        tei_logger.log('WARNING', f'{url}: TITLE TEXT NOT FOUND!')
                else:
                    tei_logger.log('WARNING', f'{url}: TITLE TAG NOT FOUND!')

            tag_root = bs.find('div', class_='field field--name-field-tags'
                                             ' field--type-entity-reference field--label-hidden field--items')
            if tag_root is not None:
                keywords_list = [t.get_text(strip=True) for t in tag_root.find_all('a')
                                 if t.get_text(strip=True) is not None]

                if len(keywords_list) > 0:
                    data['sch:keywords'] = keywords_list
            else:
                tei_logger.log('DEBUG', f'{url}: KEYWORD TAGS NOT FOUND!')

            # SOURCE
            # Some text articles indicate source at the end
            # see: https://alfahir.hu/szaud_arabia_elhozta_a_poklot

            # Sometimes explicitly
            source_in_text_tag = article_root.find(
                'div', class_='field field--name-field-forras field--type-string field--label-inline')
            if source_in_text_tag is not None:
                source_in_text_tag_text = source_in_text_tag.find('div', class_='field--item').get_text(strip=True)
                if source_in_text_tag_text is not None:
                    data['sch:source'] = source_in_text_tag_text

            # Sometimes implicitly inserted into a <p> tag
            else:
                source_text = None
                root_all_p = article_root.find_all('p')
                if len(root_all_p) > 0:
                    source_in_text_2 = root_all_p[-1].get_text(strip=True)
                    if len(source_in_text_2) > 0:
                        if source_in_text_2[0] == '(' and source_in_text_2[-1] == ')':
                            source_text = source_in_text_2[1:-1]
                        else:
                            if len(source_in_text_2) < 40:
                                source_text = source_in_text_2.strip()
                    else:
                        source_in_text_3 = article_root.find('div',
                                                             class_='field field--name-body field--type-text-with-'
                                                                    'summary field--label-hidden field--item')

                        if source_in_text_3 is not None and len(root_all_p) == 3:
                            source_in_text_4 = root_all_p[-2].get_text(strip=True)
                            if len(source_in_text_4) < 40:
                                source_text = source_in_text_4.strip()
                        elif source_in_text_3 is not None and 0 < len(root_all_p) < 3:
                            source_in_text_4 = root_all_p[-1].get_text(strip=True)
                            if len(source_in_text_4) < 40:
                                source_text = source_in_text_4.strip()
                    if source_text in SOURCE_LIST:  # Above code allows minimal mistakes - invalid sources are filtered
                        data['sch:source'] = source_text
                else:
                    tei_logger.log('DEBUG', f'{url}: SOURCE TAG NOT FOUND!')

            return data

    if root_found is False:
        tei_logger.log('WARNING', f'{url}: ARTICLE BODY NOT FOUND OR UNKNOWN ARTICLE SCHEME!')

    return None


def excluded_tags_spec(tag):
    # if tag.name not in HTML_BASICS:
    #     tag.name = 'else'
    # tag.attrs = {}
    return tag


BLOCK_RULES_SPEC = {}
BIGRAM_RULES_SPEC = {}
LINKS_SPEC = BASIC_LINK_ATTRS
DECOMP = [(('div',), {'class': 'field field-name-field-media-index-foto-video'}),
          (('div',), {'class': 'field field--name-dynamic-token-fieldnode-fb-buttons field--type-ds'
                               ' field--label-hidden field--item'}),
          (('div',), {'class': 'field field--name-dynamic-copy-fieldnode-fb-buttons2 field--type-ds'
                               ' field--label-hidden field--item'}),
          (('div',), {'class': 'field field--name-dynamic-token-fieldnode-minute-html-hook'
                               ' field--type-ds field--label-hidden field--item'}),
          (('div',), {'class': 'field field--name-dynamic-block-fieldnode-legolvasottabbak'
                               ' field--type-ds field--label-above'}),
          (('div',), {'class': 'advert_block advert_wrapper advert_mobile mobiladvert4'}),
          (('div',), {'class': 'advert_block advert_wrapper leaderboard2 advert_dektop'}),
          (('div',), {'class': 'article-content-authors'}),
          (('div',), {'class': 'article-footer'}),
          (('div',), {'class': 'article-dates'}),
          # (('div',), {'class': 'group-header'}), # contains post time
          (('div',), {'class': 'group-footer'}),
          (('div',), {'class': 'view-header'}),
          # (('div',), {'class': 'group-left'}),  # can contain post authors (not always)
          (('div',), {'class': 'fb-like'}),
          (('h4',), {'class': 'esemeny-title'}),
          (('noscript',), {}),
          # (('section',), {}),
          (('script',), {}),
          (('ins',), {})
          ]

LINK_FILTER_SUBSTRINGS_SPEC = re.compile('|'.join(['LINK_FILTER_DUMMY_STRING']))
MEDIA_LIST = [(('img',), {}),
              (('iframe',), {}),
              (('figure',), {}),
              (('blockquote',), {'class': 'embedly-card'}),
              (('div',), {'class': 'fb-page fb_iframe_widget'}),
              (('div',), {'class': 'video-embed-field-provider-youtube video-embed-field-responsive-video form-group'})]


def decompose_spec(article_dec):
    decompose_listed_subtrees_and_mark_media_descendants(article_dec, DECOMP, MEDIA_LIST)
    return article_dec


BLACKLIST_SPEC = [url.strip() for url in
                  open(os_path_join(os_path_dirname(os_path_abspath(__file__)), 'alfahir_BLACKLIST.txt')).readlines()]


MULTIPAGE_URL_END = re.compile(r'^\b$')  # Dummy


def next_page_of_article_spec(_):
    return None
