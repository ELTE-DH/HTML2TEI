# !/usr/bin/env python3
# -*- coding: utf-8, vim: expandtab:ts=4 -*-

import re

URL_ENDSWITH = re.compile(r'.*\.(hu|com|org|ro|eu)$')
URL_STARTSWITH = re.compile(r'http://|https://|www.*')
REPLACE_IN_URL = (('%2F', '/'), ('%&', '%25&'), ('[', '%5B'), (']', '%5D'), ('%?', '%25?'), ('%20', '%20'), ('%3D', '='),
                  ('%3A//', '://'), ('://://', '://'), ('http://ttp://', 'http://'), ('http://ttps://', 'https://'),
                  ('\"ttp:', 'http:'), ('\\', ''), ('Http', 'http'), ('http//www.', 'http://www.'),
                  ('\"', ''), ('http://tp://', 'http://'), ('http://ps://', 'http://'), ('https://ftp://', 'https://'),
                  ('https://ttp://', 'https://'), (': ', '%3A '), ('https://ttps://', 'https://'),
                  ('.hu:', '.hu'), ('http%2', ''),  ('.com:', '.com'))
SLASH_DOT = {'/', '.'}


def correct_first_in_link_or_facs(link, portal_url_prefix, extra_key):
    """Helper function (for link_corrector) which corrects links without prefixes (relative URL) and replaces escapes
        due to eronously concatenated URLs (facs = facsimile = href in TEI)
    """
    for origi, new in REPLACE_IN_URL:
        # This problem appeared in the articles of vs.hu, valasz.hu.
        link = link.replace(origi, new)
    link = link.strip()
    if link.startswith('//'):
        link = f'https:{link}'
    elif link.startswith('/'):
        link = f'{portal_url_prefix}{link}'
    elif not any(char in link for char in SLASH_DOT):
        if 'youtube' in extra_key:  # This problem appeared in the articles of vs.hu
            # example: <div class="_embed_youtube" data-youtube="QKZotDzTNzs">
            #  https://vs.hu/sport/osszes/bogdannak-befellegzett-liverpoolban-0111
            link = f'https://www.youtube.com/watch?v={link}'
        elif 'vimeo' in extra_key:
            link = f'https://vimeo.com/{link}'
    elif link.startswith('//infogr.am/'):   # https://infogram.com/
        link = f'https:{link}'.replace('infogr.am/', 'infogram.com')
    return link


def fix_double_or_incorrect_link(link, portal_url_prefix, portalspec_link_filter, extra_key, a_url):
    """Helper function (for link_corrector) to handle double or incorrect links
       Some links are accidentally or intentionally (web.archive) concatenated and must reconstruct them
         and choose one for the ref tag
       Examples:
         - http://web.archive.org/web/20140208052706/http://www.ox.ac.uk/...
           Source: https://vs.hu/kozelet/osszes/melegjogi-aktivistara-cserelte-orbant-az-oxfordi-egyetem-0804
         - http://A DK-sok tisztában vannak azzal, hogy ...
           http://index.hu/belfold/2016/10/10/gyurcsanyek_vegleg_kivonulnak_a_parlamentbol/
           Source: https://vs.hu/kozelet/osszes/gyurcsanyek-bojkottaljak-a-parlamentet-1010
    """
    if (link.count('http') > 1 or (' ' in link and not link.endswith('.pdf'))) and 'web.archive' not in link:
        # Example link:
        # 'http://web.archive.org/web/20140208052706/http://www.ox.ac.uk/about_the_university/oxford_people/' \
        #  'famous_oxonians/index.html'
        # in: https://vs.hu/kozelet/osszes/melegjogi-aktivistara-cserelte-orbant-az-oxfordi-egyetem-0804
        link_list = [l_url for l_url in link.split() if 'http' in l_url]
        if len(link_list) == 1:
            # Still there can be multiple concatenated links
            if link.count('http') > 1 and link.count('http:') + link.count('https:') - (
                    link.count('=http') + link.count('-http')) > 1:
                # The string "http" also can occur in the middle of a correct link:
                #  http://yamm.hu/dajcstomi/199926620658745344-http-t-co-0gv2x6qq
                link_list2 = [f'http{l_url}' for l_url in link.split('http') if len(l_url) > 0]
                link_list3 = []
                for curr_link in link_list2:
                    # WARNING Recursion! :D
                    if link_corrector(curr_link, portal_url_prefix, portalspec_link_filter, extra_key, a_url):
                        link_list3.append(curr_link)
                if len(link_list3) == 1:
                    link = link_list3[0]
                elif len(link_list3) > 1:
                    link = max(link_list3, key=len)
                else:
                    return None
        elif len(link_list) > 1:
            # TEI does not allow multiple target in ref, so we choose the longest one
            #  (the shorter ones are probably links to some immediate page)
            link = max(link_list, key=len)
        else:
            # Could not find any substring which could be interpreted as correct link
            return None
    return link


def link_corrector(link, portal_url_prefix, portalspec_link_filter, extra_key, a_url):
    """This function is the main link corrector tool to be used from outside"""
    link = link.strip()
    if link.startswith('<'):
        return None
    link = link.strip()
    if 'file://' in link:
        return None
    if portalspec_link_filter.match(link):
        return None
    link = correct_first_in_link_or_facs(link, portal_url_prefix, extra_key)
    if link.count('http') > 1:
        # Short, inappropriate string before the real link
        # "# https://..."
        start_offset = link[(link.find('http') + 1):].find('http')
        if start_offset < 11:
            link = link[start_offset + 1:]
        if link.endswith(')'):
            link = link[:-1]

    if link.count('#') > 1:
        # TEI does not allow multiple hashmark (#) in links so we delete the second one
        while link.endswith('#'):
            link = link[:-1]
        link = link[:link.find('#') + 1] + link[link.find('#') + 1:].replace('#', '%23')
    if '|||' in link:
        link = link[:(link.find('|||'))]
    if link.endswith('%'):
        link = link[:-1]
    if 'edit#gid=' in link:
        link = link[:(link.find('#gid='))]
    if '&amp;width=' in link:
        link = link[:(link.find('&amp;width='))]
    # Simple typographical errors at the beginning of the link
    http = link.find('http')
    www = link.find('www')
    if www > 0 and http == -1:
        link = link[www:]
    elif http > 0:
        link = link[http:]
    elif http < 0 and www < 0 and '/' not in link:
        # If the link neither contains "http" nor "www"
        if URL_ENDSWITH.match(link) and 'mailto' not in link:
            link = f'https://{link}'
        else:   # href="mi-a-kozeposztaly.html"  https://abcug.hu/kozeposztaly/
            return None

    link = fix_double_or_incorrect_link(link, portal_url_prefix, portalspec_link_filter, extra_key, a_url)
    if link is None:
        return None
    if link.count('/') < 3 and ('.' not in link[link.find('://') + 3:] or link.endswith('.')):
        # It filters out if plain text content if there is not / after :// at least a .something should present,
        #  else it will be treated as plain text content  e.g.
        #  https://vs.hu/kozelet/osszes/putyin-a-pok-1110 http://Center for East European Policy Studies
        return None
    elif link.endswith('.'):
        return None

    if ' ' in link and not link.endswith('.pdf') and link.count('/') < 3:
        # Those URLs which contains whitespace at this point are simple text, but could be still corrected
        #  e.g. space in the middle of the URL
        link_rep = link.replace(' - ', '-').replace('/ ', '/').replace('- ', '-')
        if link_rep == link:
            # https://vs.hu/kozelet/osszes/buda-cash-az-mnb-szerint-alaptalanok-az-ellenzek-vadjai-0302
            # http://xn--rogn antal arrl beszlt-qkc7xvk: a Fidesz kommunik%C3%A1ci%C3%B3j%C3%A1ban az %C3%BCgynek
            # %C3%BAgy kell megjelennie, hogy a Kulcs%C3%A1r-botr%C3%A1ny ut%C3%A1n a %E2%80%9Em%C3%A1sodik
            # szocialista br%C3%B3kerbotr%C3%A1nyb%C3%B3l%E2%80%9D van sz%C3%B3./
            return None
        elif link_rep != link and ' ' in link_rep:
            return None
        link = link_rep

    if link.endswith('./') or link.isalpha():
        return None

    if not URL_STARTSWITH.match(link):
        # https://vs.hu/magazin/osszes/van-valami-a-dunaujvarosi-levegoben-1226 oki.antsz.hu/#tab_levego
        # https://vs.hu/kozelet/osszes/balog-zoltan-koszoni-a-roma-holokausztrol-szolo-anyagot-0804
        # httphu.tdf-cdn.com/4638/_demand/0077ea0c_6408785.mp3
        return None

    link = ''.join(link.split('\n'))

    if '.,' in link:
        pass

    return link
