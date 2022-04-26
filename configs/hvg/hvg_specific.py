#!/usr/bin/env python3
# -*- coding: utf-8, vim: expandtab:ts=4 -*

import re
from bs4 import BeautifulSoup
from html2tei import parse_date, BASIC_LINK_ATTRS, decompose_listed_subtrees_and_mark_media_descendants, tei_defaultdict

PORTAL_URL_PREFIX = 'https://hvg.hu/'

ARTICLE_ROOT_PARAMS_SPEC = [(('div',), {'class': 'article-main'})]

HTML_BASICS = {'p', 'h3', 'h2', 'h4', 'h5', 'em', 'i', 'b', 'strong', 'mark', 'u', 'sub', 'sup', 'del', 'strike',
               'ul', 'ol', 'li', 'table', 'tr', 'td', 'th', 'quote', 'figure', 'iframe', 'script', 'noscript'}

SOURCE = ['hvg.hu', 'MTI', 'MTI/hvg.hu', 'MTI / hvg.hu', 'Marabu', 'HVG', 'Eduline', 'Reuters', 'honvedelem.hu', 'BBC',
          'Euronews', 'EUrologus', 'OS', 'Dow Jones', 'DPA', 'DW', 'Hszinhua', 'MTA', 'AP', 'AFP', 'HVG Konferencia',
          'Zgut Edit', 'Index', 'foodnetwork', 'mult-kor.hu', 'MT Zrt.', 'élelmiszer online', 'atlatszo.blog.hu',
          'Blikk', 'HVG Extra Business', 'Origo', 'Bors', '- esel -', 'Magyar Nemzet', 'EFE', 'merites.hu',
          'Népszabadság', 'Inforádió', 'HVG Extra Pszichológia', 'MTI-OS', 'MLF', 'ITAR-TASZSZ', 'MNO',
          'MR1-Kossuth Rádió', 'HavariaPress', 'CNN', 'Bank360.hu', 'Bankmonitor.hu', 'ingatlanmenedzser.hu', 
          'HavariaPress/hvg.hu', 'Jobline.hu', 'MTI/honvedelem.hu', 'Adozona.hu', 'f1-live.hu', 'eduline.hu', 
          'pecsma.hu', 'hvg.hu/vendeglatasmagazin.hu', 'MTI-OS/hvg.hu', 'hvg.hu/termekmix.hu', 'hvg.hu/D.P.', 
          'Utinform.hu', 'szoljon.hu', 'hvg.hu/napi.hu', 'police.hu', 'delmagyar.hu', 'sonline.hu', 
          'hvg.hu/atlatszo.blog.hu', 'I.N./hvg.hu', 'kisalföld.hu', 'hvg.hu/MTI/Blikk', 'hvg.hu/VinceBudapest', 
          'hvg.hu/muosz.hu', 'hvg.hu/transindex.ro', 'hvg.hu/manna.ro', 'nso.hu', 'f1-live/hvg.hu', 'kemma.hu', 
          'met.hu', 'baon.hu', 'HVG/hvg.hu', 'Számlázz.hu', 'VG/hvg.hu', 'hvg.hu/merites.hu', 'teol.hu', 'dehir.hu', 
          'hvg.hu/Blikk', 'hvg.hu/Origo', 'hvg.hu/MTI', 'Napi.hu', 'hvg.hu/Travellina', 'hirado.hu', 'indohaz.hu', 
          'hvg.hu/HVG', 'portfolio.hu', 'hvg.hu/HavariaPress', 'hvg.hu/turizmus.com', 'hvg.hu/mult-kor.hu', 'hvg.hu/benke', 
          'hvg.hu/Index', 'hvg.hu/MTI/HavariaPress', 'BiztosDöntés.hu', 'hvg.hu/termekmix.com', 'nyugat.hu', 
          'bankmonitor.hu', 'Népszava/hvg.hu', 'hvg.hu/foodnetwork', 'hvg.hu/businesstraveller', 'MTI/HavariaPress', 
          'MTI/AP/REUTERS', 'MTI/Reuters', 'MTI/Reuters/DPA', 'MTI/Észak-Magyarország', 'MTI/Reuters/AFP', 
          'MTI/Világgazdaság', 'TV2/Tények', 'MTI/AFP/AP/Reuters', 'HavariaPress/MTI', 'MTI/ITAR-TASZSZ', 
          'MTI/dpa/EFE/Reuters', 'MTI/Népszabadság', 'MTI/AFP/DPA', 'MTI/Kisalföld', 'MTI/EFE', 'MTI/AFP', 
          'MTI/DPA/AP', 'MTI/AP/AFP', 'MTI/Index', 'MTI/DPA', 'MTI/AFP/AP/ITAR-TASZSZ', 'MTI/InfoRádió', 
          'MTI/Népszava', 'MTI/dpa/Hszinhua', 'OTS/MTI', 'BBC/MTI', 'MTI/Bors', 'MTI/Reuters/AP', 'MTI/AP', 
          'MTI/AFP/Reuters', 'MTI/Reuters/Hszinhua', 'MTI/Blikk', 'HVG/MTI']


def get_meta_from_articles_spec(tei_logger, url, bs):
    data = tei_defaultdict()
    data['sch:url'] = url
    article_root = bs.find('div', class_='article-content')
    if article_root is not None:
        date_tag = bs.find('time', class_='article-datetime')
        if date_tag is not None and 'datetime' in date_tag.attrs.keys():
            parsed_date = parse_date(date_tag.attrs['datetime'][:19], '%Y-%m-%dT%H:%M:%S')
            data['sch:datePublished'] = parsed_date
        else:
            tei_logger.log('WARNING', f'{url}: DATE TAG NOT FOUND!')
        modified_date_tag = bs.find('time', class_='lastdate')
        if modified_date_tag is not None and 'datetime' in modified_date_tag.attrs.keys():
            parsed_modified_date = parse_date(modified_date_tag.attrs['datetime'][:19], '%Y-%m-%dT%H:%M:%S')
            data['sch:dateModified'] = parsed_modified_date
        else:
            tei_logger.log('DEBUG', f'{url}: MODIFIED DATE TAG NOT FOUND!')
        title = article_root.find('div', class_='article-title article-title')
        if title is not None:
            article_title = title.find('h1')
            data['sch:name'] = article_title.text.strip()
        else:
            tei_logger.log('WARNING', f'{url}: TITLE TAG NOT FOUND!')
        author_or_source_tag = article_root.find('div', class_='author-name')
        if author_or_source_tag is not None:
            author_or_source = author_or_source_tag.text.strip().\
                replace('\r', '').replace('\n', '').replace('\t', '').replace('Követés', '')
            if author_or_source in SOURCE:
                data['sch:source'] = [author_or_source]
            else:
                data['sch:author'] = [author_or_source]
        else:
            tei_logger.log('DEBUG', f'{url}: AUTHOR / SOURCE TAG NOT FOUND!')
        keywords_root = article_root.find('div', class_='article-tags')
        if keywords_root is not None:
            keywords_list = [t.text.strip() for t in keywords_root.find_all('a') if t is not None]
            data['sch:keywords'] = keywords_list
        else:
            tei_logger.log('DEBUG', f'{url}: TAGS NOT FOUND!')
        info_root = bs.find('div', class_='info')
        if info_root is not None:
            section_main = info_root.find('a')
            if section_main is not None:
                data['sch:articleSection'] = section_main.text.strip()
            else:
                tei_logger.log('WARNING', f'{url}: SECTION TAG NOT FOUND!')
        return data
    else:
        # hvg360 format https://hvg.hu/360/20210704_Hatvanpuszta_major_orban_Viktor_orban_Gyozo
        hvg360format = bs.find('div', {'class': ['article-body']})
        if hvg360format is not None:
            # author
            script_tags = bs.find_all('script', {'type': True})
            if len(script_tags) > 1:
                script_tags = bs.find_all('script', {'type': True})[1].get_text()
                author_beg = script_tags.find('author:{id')
                author_end = author_beg+script_tags[author_beg:].find('}')
                auth_string = script_tags[author_beg:author_end]
                beg = auth_string.find('"')
                end = auth_string[beg+1:].find('"')+beg
                if beg != -1 and end != -1:
                    author = auth_string[beg+1:end+1]
                    data['sch:author'] = [author]
                else:
                    tei_logger.log('DEBUG', f'{url} NO AUTHOR FOUND!')

            # title
            article_tag = bs.find('article')
            if article_tag is not None:
                title_tag = article_tag.find('h1')
                if title_tag is not None:
                    title = title_tag.get_text(strip=True)
                    if len(title) > 0:
                        data['sch:name'] = title
                    else:
                        tei_logger.log('WARNING', f'{url} TITLE TAG EMPTY!')
                else:
                    tei_logger.log('WARNING', f'{url} TITLE TAG NOT FOUND!')

            # date published and date modified
            header_tag = bs.find('div', {'class': 'meta column mb-4 mb-xl-5'})
            if header_tag is not None:
                p_tags = header_tag.find_all('p', {'class': 'text-bold'})
                if len(p_tags) > 1:
                    pub_date_text = p_tags[-1].get_text(strip=True)
                    if len(pub_date_text) > 0:
                        parsed_pub = parse_date(pub_date_text, '%Y.%m.%d. %H:%M')
                        if parsed_pub is not None:
                            data['sch:datePublished'] = parsed_pub
                        else:
                            tei_logger.log('WARNING', f'{url} FAILED TO PARSE PUBLISH DATE!')
                    else:
                        tei_logger.log('WARNING', f'{url} PUBLISH DATE TAG EMPTY!')
                else:
                    tei_logger.log('WARNING', f'{url} PUBLISH DATE TAG NOT FOUND!')
                # date modified
                modified_tag = header_tag.find('div', {'class': 'item d-none d-xl-inline-block'})
                if modified_tag is not None:
                    date_modified_tag = modified_tag.find('p')
                    if date_modified_tag is not None:
                        date_modified = date_modified_tag.get_text(strip=True)
                        if len(date_modified) > 0:
                            parsed_mod = parse_date(date_modified, '%Y.%m.%d. %H:%M')
                            if parsed_mod is not None:
                                data['sch:dateModified'] = parsed_mod
                            else:
                                tei_logger.log('WARNING', f'{url} FAILED TO PARSE MODIFICATION DATE!')
                        else:
                            tei_logger.log('DEBUG', f'{url} MODIFICATION DATE TAG EMPTY!')
            # article section
            article_section_tag = bs.find('span', {'class':'tag text-nowrap tag-big tag-inactive'})
            if article_section_tag is not None:
                article_section = article_section_tag.get_text(strip=True)
                if article_section is not None:
                    data['sch:articleSection'] = article_section
            else:
                tei_logger.log('WARNING', f'{url} ARTICLE SECTION NOT FOUND!')

            # keywords
            keywords_meta = bs.find('meta', {'data-n-head': True, 'name': 'exclusiontags', 'content': True})
            if keywords_meta is not None:
                keywords = keywords_meta['content'].split(',')
                if len(keywords) > 0:
                    data['sch:keywords'] = keywords
            else:
                tei_logger.log('DEBUG', f'{url} NO KEYWORDS FOUND')

        else:
            tei_logger.log('WARNING', f'{url}: ARTICLE BODY NOT FOUND!')
    return data


def excluded_tags_spec(tag):
    return tag


BLOCK_RULES_SPEC = {}
BIGRAM_RULES_SPEC = {}
LINKS_SPEC = BASIC_LINK_ATTRS
DECOMP = [(('script',), {}),
          (('meta',), {}),
          (('div',), {'class': 'placeholder-ad'}),
          (('div',), {'class': 'article-series-box'}),
          (('button',), {}),
          (('div',), {'class': 'G-pagination'}),
          ]

bad_url_list = ['/2016.03.10 14:25:00',
                '/2020.09.10 11:03:00',
                '/2019.11.12 20:03:00',
                '/Előző számaink tartalmából:',
                'https://www.consilium.europa.eu/hu/press/press-releases/2021/05/',
                'https://hvg.hu//Az%20als%C3%B3%20rakparti%20utak%20lez%C3%A1r%C3%A1sa%20miatt%20Budapest%20bels%C5%91%20ter%C3%BCletein%20%C3%A9s%20gerinc%C3%BAtvonalain%20jelent%C5%91sen%20megn%C3%B6vekedett%20a%20k%C3%B6z%C3%BAti%20forgalom,%20ez%C3%A9rt%20az%20ott%20k%C3%B6zleked%C5%91%20j%C3%A1rataink%20eset%C3%A9ben%20is%20n%C5%91tt%20a%20menetid%C5%91.%20Jelenleg%20az%20al%C3%A1bbi%20aut%C3%B3buszj%C3%A1ratainkon%20kell%20hosszabb%20menetid%C5%91re%20sz%C3%A1m%C3%ADtani',
                ]
LINK_FILTER_SUBSTRINGS_SPEC = re.compile('|'.join([re.escape(s) for s in bad_url_list]))
MEDIA_LIST = []

hvg_fb_links = ['hvgkult',
                'hvghunagyitas', 
                'hvg.hu.eletstilus',
                'hvg.tech',
                'hvgauto',
                'hvgkonyvek',
                'hvgextrapszichologiamagazin',
                'hvgkonferenciak',
                'hvghu',
                'hvgextraano']

def decompose_spec(article_dec):
    decompose_listed_subtrees_and_mark_media_descendants(article_dec, DECOMP, MEDIA_LIST)
    # Delete menu h2 tag for news feed articles
    for f in article_dec.find_all('h2', {'class': 'larger-header'}):
        if f.find('div', {'class': 'article-pp_change_order'}) is not None:
            f.decompose()
    # Delete mid-page facebook embeds of hvg facebook page
    for f in reversed(article_dec.find_all('div', {'class':'fb-page', 'data-href': True})):
        if f['data-href'] in hvg_fb_links:
            f.decompose()
    # Delete end of article hvg facebook page embed
    for t in article_dec.find_all('iframe', {'src':True}):
        if any(s in t['src'] for s in hvg_fb_links):
            t.decompose()

    for p in article_dec.find_all('p'):
        if len(p.find_all('a', {'href': True})) == 1:
            if any(ext in p.find('a', {'href': True})['href'] for ext in hvg_fb_links):
                p.decompose()
    
    # Delete embedded hvg.hu articles
    blockquotes = article_dec.find_all('blockquote')
    for bl in blockquotes:
        bl_a = bl.find('a', {'href':True})
        if bl_a is not None and len(bl_a['href'].split('/')) > 2 and bl_a['href'].split('/')[2] == 'hvg.hu':
            bl.decompose()

    return article_dec


BLACKLIST_SPEC = [
    # Faulty html - extra <!DOCTYPE html> tag
    'https://hvg.hu/ingatlan/20171031_Megint_lokhet_egyet_a_lakashitelesek_ugyen_az_MNB',
    'https://hvg.hu/gazdasag/20171011_Lakast_vasarol_es_lecsapna_az_allami_ingyenpenzre_Mutatjuk_a_nyolc_kezenfekvo_megoldast',
    'https://hvg.hu/gazdasag/20170925_Gyereknek_lakast_hitelbol',
    'https://hvg.hu/ingatlan/20171109_Tenyleg_jobban_megeri_ingatlankozvetitot_nyitni_mint_a_lakaskiadassal_bibelodni',
    'https://hvg.hu/ingatlan/20171028_Nyaralot_venne_Jobban_jar_ha_var_vele',
    'https://hvg.hu/gazdasag/20171016_Mire_eleg_egy_tizmillios_lakashitel_Egyetlen_abran_minden_az_orszagos_arakrol',
    'https://hvg.hu/gazdasag/20171103_Duplajara_nott_az_epitesi_kedv_nagyobbak_a_lakasok_is',
    'https://hvg.hu/gazdasag/20180215_hitel_kolcson_penz_atveres_csalas_bankok_tudnivalo_video',
    'https://hvg.hu/gazdasag/20180208_Sokkolo_szamok_a_nyugateuropaiaknak_tizszer_annyi_megtakaritasuk_van_mint_a_magyaroknak',
    'https://hvg.hu/ingatlan/20171026_Alcazott_probavasarlok_teszteltek_a_lakashiteleket_ajanlo_bankokat_itt_az_eredmeny',
    'https://hvg.hu/gazdasag/20171215_Tudja_mi_a_lakashitelt_igenylok_nagy_dilemmaja_Mutatjuk_es_segitunk_feloldani',
    'https://hvg.hu/gazdasag/20171025_A_fiatal_par_szinte_nullara_hozta_ki_a_lakashitel_kamatat_mutatjuk_hogyan',
    'https://hvg.hu/gazdasag/20171103_Mennyit_es_meddig_kell_felretenni_lakastakarekba_hogy_lakas_is_legyen_belole_Itt_az_orszagos_abra',
    'https://hvg.hu/ingatlan/20171109_Csak_akkor_csereld_a_panelt_lakoparkra_ha_ezeket_merlegeled',
    'https://hvg.hu/gazdasag/20171020_Jovore_erik_a_gyerek_Mutatjuk_milyen_kiadasokkal_jar_ez_a_csaladnak',
    'https://hvg.hu/gazdasag/20171130_A_bank_vagy_a_lakastakarek_a_nyero_ha_hitel_kell_a_lakasvasarlashoz_Kiszamoltuk',
    'https://hvg.hu/gazdasag/20180216_befektetes_penz_nyereseg_lakastakarek_hozam_kamat_haszon',
    'https://hvg.hu/gazdasag/20180221_Nagyobb_lakasba_koltozne_a_csalad_Mutatjuk_a_kethiteles_kevesek_altal_ismert_megoldast',
    'https://hvg.hu/gazdasag/20171013_Alberlethez_igenyelne_tamogatast_Van_egy_jo_es_eleg_sok_rossz_hirunk',
    'https://hvg.hu/ingatlan/20180324_Itt_eri_meg_most_a_lakasbefektetes_de_bukni_is_lehet',
    # HVG 360 articles:
    'https://hvg.hu/360/20210704_Hatvanpuszta_major_orban_Viktor_orban_Gyozo',
    'https://hvg.hu/360/20200217_Orbanertekeles_2020',
    'https://hvg.hu/360/20190619_Koszeg_Ferenc_velemeny',
    # Empty articles:
    'https://hvg.hu/kkv/20171107_rudi_kviz_pottyos_turos',
    'https://hvg.hu/gazdasag/20181109_Ujra_eladta_a_sirkoves_a_temetokbol_lopott_vazakat',
    'https://hvg.hu/itthon/20130212_Havazas_20130212',
    'https://hvg.hu/hvgkonyvek/20191119_Az_ertekesites_titkos_kodja__avagy_mi_kulonbozteti_meg_a_gyozteseket',
    'https://hvg.hu/gazdasag/20180629_Harom_miniszter_is_elment_Szegedre_egy_fektelep_atadasara',
    'https://hvg.hu/gazdasag/20200511_uzemanyag_benzin_gazolaj',
    'https://hvg.hu/elet/20190330_On_melyik_idoszamitast_tartana_meg_Szavazzon',
    'https://hvg.hu/elet/20170804_Csobbanak_es_dinnyeznek_a_jegesmedvek_az_Allatkertben',
    'https://hvg.hu/sport/20130201_Uj_Ferrari',
    'https://hvg.hu/hvgkonyvek/20200105_Eric_Idle_Monty_Python_konyv',
    'https://hvg.hu/plazs/20160401_Hosszu_Katinka_kopasz',
    'https://hvg.hu/vilag/20160510_Dronfelvetelrol_is_megnezheti_a_gyozelem_napi_moszkvai_tuzijatekot',
    'https://hvg.hu/vilag/20170924_Macron_partjanak_nem_sikerult_az_attores_a_szenatusban',
    'https://hvg.hu/sport/20180325_Forma1_Vettel_nyerte_az_idenynyitot',
    'https://hvg.hu/elet/20200509_Csak_ugy_potyognak_az_elefantbebik_a_pragai_allatkertben',
    'https://hvg.hu/vilag/20130215_Oroszorszag_meteor',
]

# def transform_to_html(url, raw_html, warc_logger):
#     _ = url  # , warc_logger

#     soup = BeautifulSoup(raw_html, 'html.parser')
#     html_tags = soup.find_all('html')
#     if len(html_tags) == 2:
 
#         # a few websites contain faulty html code: an extra <!DOCTYPE html> is included
#         doctype_text = '<!DOCTYPE html>'
#         first_index = str(soup).find(doctype_text)
#         first_index = first_index + len(doctype_text)
#         second_index = str(soup)[first_index:].find(doctype_text)
#         if second_index != -1:
#             second_index = second_index + first_index
#             end_index = str(soup)[second_index:].find('</html>')
#             end_index = second_index + end_index + len('</html>')
#             fixed_string = str(soup).replace(str(soup)[second_index:end_index], '')
#             return fixed_string
#     return raw_html

MULTIPAGE_URL_END = re.compile(r'.*\?isPrintView.*')
# https://hvg.hu/sport/20210614_foci_eb_euro_2020_junius_14_percrol_percre/2?isPrintView=False&liveReportItemId=0&isPreview=False&ver=1&order=desc


def next_page_of_article_spec(curr_html):
    bs = BeautifulSoup(curr_html, 'lxml')
    if bs.find('div', class_='G-pagination') is not None:
        next_tag = bs.find('a', {'class': 'arrow next', 'rel': 'next', 'href': True})
        if next_tag is not None:
            next_link = next_tag.attrs['href'].replace('amp;', '')
            link = f'https://hvg.hu{next_link}'
            print(link)
            return link
    return None
