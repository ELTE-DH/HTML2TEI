# !/usr/bin/env python3
# -*- coding: utf-8, vim: expandtab:ts=4 -*-

from io import BytesIO
from zipfile import ZipFile
from unicodedata import normalize
from urllib.parse import urlparse
from urllib.request import urlopen
from re import compile as re_compile
from os import getcwd, makedirs, listdir
from os.path import basename as os_path_basename, isabs as os_path_isabs, isdir as os_path_isdir, \
    exists as os_path_exists, abspath as os_path_abspath, join as os_path_join

from lxml import etree

from html2tei.digest import MtHasher, ALGORITHMS_GUARANTEED

NOT_ALNUM_WS_OR_DASH = re_compile(r'[^\w\s-]')
MORE_DASH_OR_WS = re_compile(r'[-\s]+')

# Only init_output_writer is used outside of this file


def init_output_writer(output_dir, portal_name, output_debug, tei_logger):
    """Initialises the class for writing output:
        1. Normal mode: valid XMLs go into a zip file, invalid ones go to output_dir directory
         while a separate file is created to store the hashsums of the zipped files (all filenames are UUIDs)
        2. Debug mode: all XMLs go into output_dir directory (all filenames are slugs from the URL)
    """
    if output_debug:
        output_writer_class = StoreFilesWithReadableName
    else:
        output_writer_class = ValidatorHasherCompressor
    output_writer = output_writer_class(tei_logger, os_path_join(output_dir, f'{portal_name}_not_valid'),
                                        os_path_join(output_dir, f'{portal_name}.zip'),
                                        os_path_join(output_dir, f'{portal_name}.hashsums'))
    return output_writer


def slugify(value, allow_unicode=True):
    """
    Original source:
    https://github.com/django/django/blob/af609c2f4d3fd22bc9ffa12a844df282ce233936/django/utils/text.py#L386
    Convert to ASCII if 'allow_unicode' is False. Convert spaces or repeated
    dashes to single dashes. Remove characters that aren't alphanumerics,
    underscores, or hyphens. Convert to lowercase. Also strip leading and
    trailing whitespace, dashes, and underscores.
    """
    value = str(value)
    if allow_unicode:
        value = normalize('NFKC', value)
    else:
        value = normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
    value = NOT_ALNUM_WS_OR_DASH.sub('', value.lower())
    return MORE_DASH_OR_WS.sub('-', value).strip('-_')


def init_directory(bad_urls_dir, tei_logger):
    """Initialise bad_urls_dir:
       1. Resolve path (absolute or relative to the working directory)
       2. Check if not exists and create it (warn if exists)
       3. Check if bad_urls_dir is a directory (fail gracefully if it is other than directory)
       4. Check if bad_urls_dir empty (warn if not)
    """
    if not os_path_isabs(bad_urls_dir):
        bad_urls_dir = os_path_join(os_path_abspath(getcwd()), bad_urls_dir)
    if os_path_exists(bad_urls_dir):
        tei_logger.log('WARNING', f'{bad_urls_dir} exists!')
    else:
        makedirs(bad_urls_dir, exist_ok=True)
    if not os_path_isdir(bad_urls_dir):
        tei_logger.log('CRITICAL', f'{bad_urls_dir} is not a directory!')
        exit(1)
    if len(listdir(bad_urls_dir)) > 0:
        tei_logger.log('WARNING', f'{bad_urls_dir} is not empty!')
    return bad_urls_dir


def check_for_filename_collision(url, desired_filename, filename_suff, assigned_filenames, tei_logger):
    """This  function ensures no output files will be overwritten during processing
        Check if the filename already assigned or not. If it is, then it will try to generate a new name
        by adding a number suffix 100 times before giving up and failing
    """
    final_name = f'{desired_filename}{filename_suff}'
    for i in range(100):
        if final_name not in assigned_filenames:  # If it is already assigned, modify the filename!
            break
        final_name = f'{desired_filename}_{i}{filename_suff}'
        assigned_filenames.add(final_name)
    else:
        tei_logger.log('CRITICAL', f'Too much URL with same name {url} !')
        exit(1)
        final_name = None
    return final_name


class StoreFilesWithReadableName:
    """Store output files in bad_urls_dir directory for later examination
        (no zipping, no validation, filenames are slugified urls)
    """
    def __init__(self, tei_logger, bad_urls_dir, zipfile_name=None, hashsums_filename=None, hash_algos=None,
                 tei_schema=None):
        # To be a drop-in replacement
        _ = zipfile_name, hashsums_filename, hash_algos, tei_schema

        # Init directory
        self._bad_urls_dir = init_directory(bad_urls_dir, tei_logger)

        self._tei_logger = tei_logger
        self._assigned_filenames = set()

    def process_one_file(self, url, desired_filename, filename_suff, raw_xml_str):
        _ = desired_filename  # This contains the UUID
        if url.endswith('/'):
            url = url[:-1]
        # The last segment (249 characters) of the URL something.html or .../something/ (trailing slash omitted)
        desired_filename = f'{os_path_basename(urlparse(url).path)[:249]}'.replace('/', '_')
        desired_filename_slug = slugify(desired_filename)
        xml_filename = check_for_filename_collision(url, desired_filename_slug, filename_suff, self._assigned_filenames,
                                                    self._tei_logger)
        with open(os_path_join(self._bad_urls_dir, xml_filename), 'wb') as fh:
            fh.write(raw_xml_str)

        return xml_filename


class ValidatorHasherCompressor:
    """Validate output TEI XML files, zip the valid ones and compute their hashsums, invalid XMLs go
        to bad_urls_dir directory with UUID filenames"""
    def __init__(self, tei_logger, bad_urls_dir, zipfile_name, hashsums_filename, hash_algos=ALGORITHMS_GUARANTEED,
                 tei_schema='https://tei-c.org/release/xml/tei/custom/schema/relaxng/tei_all.rng'):
        # Init Zipfile
        self._zipfile = ZipFile(zipfile_name, 'w')

        # Setup RelaxNG validator
        with urlopen(tei_schema) as response:
            tei_schema_str = response.read()
        relaxng_doc = etree.fromstring(tei_schema_str)
        # LXML FAQ: You can share RelaxNG, XMLSchema and (with restrictions) XSLT objects between threads.
        self._validator = etree.RelaxNG(relaxng_doc)

        # Init Hasher
        self._hasher = MtHasher(hash_algos)

        # Init hashsums file
        self._hashsums_fh = open(hashsums_filename, 'w', encoding='UTF-8')
        print(*self._hasher.header, sep='\t', file=self._hashsums_fh)

        # Init directory
        self._bad_urls_dir = init_directory(bad_urls_dir, tei_logger)

        self._tei_logger = tei_logger
        self._assigned_filenames = set()

    def __del__(self):
        # Else essential records will not be written!
        zipfile = getattr(self, '_zipfile', None)
        if zipfile is not None:
            close = getattr(zipfile, 'close', None)
            if close is not None:
                close()

    def process_one_file(self, url, desired_filename, filename_suff, raw_xml_str):

        xml_etree = etree.fromstring(raw_xml_str)
        xml_filename = check_for_filename_collision(url, desired_filename, filename_suff, self._assigned_filenames,
                                                    self._tei_logger)
        out_filename = os_path_basename(xml_filename)
        try:
            self._validator.assert_(xml_etree)
            valid = True
        except AssertionError as err:
            self._tei_logger.log('ERROR', 'TEI validation error:', url, out_filename, err)
            valid = False
        if valid:
            digests = self._hasher.hash_file(BytesIO(raw_xml_str))
            self._zipfile.writestr(xml_filename, raw_xml_str)
            print(out_filename, url, *digests, sep='\t', file=self._hashsums_fh)
        else:
            with open(os_path_join(self._bad_urls_dir, out_filename), 'wb') as fh:
                fh.write(raw_xml_str)

        return xml_filename
