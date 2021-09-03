#!/usr/bin/env python3
# -*- coding: utf-8, vim: expandtab:ts=4 -*-

import sys
from os.path import join as os_path_join

from html2tei.read_config import check_exists


def diff_all_tag_table(diff_dir, old_filename, new_filename, out_filename):
    """This function compares the old table with a new one.
       It keeps the 6th and 7th columns which were manually corrected,
         so deleting decompose and updated_old yields the fresh table.
       One must check the rows marked with NEW and may check rows with updated_new
         to allow the user to change his or her decision in the light of the new numbers
       The 8th row of new table created from the comparison consists of the following values:
         1) OK: unchanged row
         2) decomposed: missing tag/tagname changed
         3) NEW: new tag
         4) updated_new: any of the four numbers are changed (updated_old contains the old values)
    """
    old_filename_w_path = os_path_join(diff_dir, old_filename)
    new_filename_w_path = os_path_join(diff_dir, new_filename)
    out_filename_w_path = os_path_join(diff_dir, out_filename)
    check_exists(old_filename_w_path)
    check_exists(new_filename_w_path)

    with open(old_filename_w_path, encoding='UTF-8') as old_table, \
            open(new_filename_w_path, encoding='UTF-8') as new_table, \
            open(out_filename_w_path, 'w', encoding='UTF-8') as out_table:
        # 1) Read old table -> dict, new table -> dict
        # For convenience we split the values into two tuples:
        #  the numeric properties (frequency, avg. len. of text, avg. no. of descendants, avg. len. of immediate text)
        #  and the the rest which are actually compared (all links, category, normal name)
        old_dict = table_to_dict(old_table, old_filename_w_path)
        new_dict = table_to_dict(new_table, new_filename_w_path)
        for old_tag, (num_properties, links_and_rating) in old_dict.items():  # Traverse the old table
            freq, avg_len_of_text, avg_no_of_descendants, avg_len_of_immediate_text = num_properties
            if old_tag in new_dict.keys():
                if num_properties == new_dict[old_tag][0]:
                    difference_class = 'OK'  # Values unchanged
                else:
                    difference_class = 'updated_old'  # Kept for double checking (easy to delete later)
            else:
                difference_class = 'decomposed'  # Does not appear in the new values
            print(freq, old_tag, avg_len_of_text, avg_no_of_descendants, avg_len_of_immediate_text,
                  *links_and_rating, difference_class, sep='\t', file=out_table)
        for new_tag, (new_num_properties, links_and_rating) in new_dict.items():
            freq, avg_len_of_text, avg_no_of_descendants, avg_len_of_immediate_text = new_num_properties
            if new_tag not in old_dict.keys():
                difference_class = 'NEW'  # New label
                print(freq, new_tag, avg_len_of_text, avg_no_of_descendants, avg_len_of_immediate_text,
                      *links_and_rating, difference_class, sep='\t', file=out_table)
            elif new_tag in old_dict.keys() and new_num_properties != (old_dict[new_tag][0]):
                # The label is contained in the old table but with different numbers
                # (we keep the old values for comparison)
                difference_class = 'updated_new'
                print(freq, new_tag, avg_len_of_text, avg_no_of_descendants, avg_len_of_immediate_text,
                      *old_dict[new_tag][1], difference_class, sep='\t', file=out_table)


def table_to_dict(new_table, table_name):
    """Helper function to read the tables"""
    ret_dict = {}
    for i, line in enumerate(new_table, start=1):
        try:
            freq, tag_excl_name, avg_len_of_text, avg_no_of_descendants, avg_len_of_immediate_text, all_links, \
                category, normal_name = (col.strip() for col in line.strip().split('\t'))
            ret_dict[tag_excl_name] = ((freq, avg_len_of_text, avg_no_of_descendants, avg_len_of_immediate_text),
                                       (all_links, category, normal_name))
        except ValueError:
            print(f'ValueError at {i}th line of {table_name} table', file=sys.stderr)
            exit(1)
    return ret_dict
