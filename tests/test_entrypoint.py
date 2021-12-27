#!/usr/bin/env python3
# -*- coding: utf-8, vim: expandtab:ts=4 -*-

from io import StringIO
from pathlib import Path
# from pprint import pprint
# import pytest

import html2tei


def get_pairs():
    """Return with pairs of input - expected output files.
    """
    input_dir = Path('tests/input')
    gold_dir = Path('tests/gold')
    pairs = ((x, (gold_dir / x.name).with_suffix('.tsv')) for x in input_dir.glob('*'))
    return pairs


def test_entrypoint():
    # TODO
    """
    for inp_path, gold_path in get_pairs():
        with open(inp_path) as inp_stream, open(gold_path) as gold_stream:
            out_stream = StringIO()
            entrypoint(inp_stream, out_stream)
            out_stream.seek(0)
            for index, (actual_line, expected_line) in enumerate(zip(out_stream.readlines(), gold_stream.readlines())):
                assert actual_line == expected_line, f'ERROR: file: {inp_path}; line: {index}'
    """

# def main():
#     print('TEST MAIN')


if __name__ == '__main__':
    # main()
    pass
