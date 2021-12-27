#!/usr/bin/env python3
# -*- coding: utf-8, vim: expandtab:ts=4 -*-

from argparse import ArgumentParser, ArgumentTypeError

from html2tei.processing_utils import run_main
from html2tei.read_config import WRITE_OUT_MODES
from html2tei.update_and_filter_tables import diff_all_tag_table
from html2tei.tag_bigrams_maker import init_portal as tag_bigrams_init_portal
from html2tei.html_content_tree import init_portal as content_tree_init_portal
from html2tei.tag_inventory_maker import init_portal as tag_inventory_init_portal
from html2tei.portal_article_cleaner import init_portal as portal_article_cleaner_init_portal


def str2bool(v):
    """
    Original code from:
     https://stackoverflow.com/questions/15008758/parsing-boolean-values-with-argparse/43357954#43357954
    """
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise ArgumentTypeError('Boolean value expected.')


def entrypoint():
    parent_parser = ArgumentParser(prog='html2tei')

    command_dict = {'cleaner': (portal_article_cleaner_init_portal, 'Portal Article Cleaner'),
                    'inventory-maker': (tag_inventory_init_portal, 'Tag Inventory Maker'),
                    'bigram-maker': (tag_bigrams_init_portal, 'Tag Bigrams Maker'),
                    'content-tree': (content_tree_init_portal, 'HTML Content Tree')
                    }

    common_params = {'input_config': (('-i', '--input-config'),
                                      {'type': str, 'help': 'WARC filename to portal name mapping in YAML',
                                       'metavar': 'FILE.yaml', 'required': True}),
                     'configs_dir': (('-c', '--configs-dir'),
                                     {'type': str, 'help': 'The directory for portal-specific configs',
                                      'metavar': 'DIR', 'required': True}),
                     'log_dir': (('-l', '--log-dir'),
                                 {'type': str, 'help': 'The directory for putting logs', 'metavar': 'DIR',
                                  'required': True}),
                     'warc_dir': (('-w', '--warc-dir'),
                                  {'type': str, 'help': 'The directory to read WARCs from', 'metavar': 'DIR',
                                   'required': True}),
                     'output_dir': (('-o', '--output-dir'),
                                    {'type': str, 'help': 'The directory to put output files', 'metavar': 'DIR',
                                     'required': True}),
                     'log_level': (('-L', '--log-level'),
                                   {'type': str, 'choices': {'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'},
                                    'help': 'Log verbosity level (default: INFO)', 'default': 'INFO',
                                    'metavar': 'LEVEL'})
                     }

    subparsers = parent_parser.add_subparsers(help='Running mode', dest='command', required=True,
                                              metavar='MODE')

    # For each subparser define the common arguments (to ensure the ordering of arguments)
    spdict = {}
    for cmd, (_, help_text) in command_dict.items():
        p = subparsers.add_parser(cmd, help=help_text)
        for _, (args, kwargs) in common_params.items():
            p.add_argument(*args, **kwargs)
        spdict[cmd] = p

    spdict['cleaner'].add_argument('-m', '--write-out-mode', type=str, choices=WRITE_OUT_MODES.keys(), default='eltedh',
                                   help='The schema removal tool to use (ELTEDH, JusText, Newspaper3k)', metavar='MODE')

    spdict['cleaner'].add_argument('-t', '--task-name', type=str, default='Portal Article Cleaner',
                                   help='The name of the task to appear in the logs', metavar='TASK_NAME')

    spdict['cleaner'].add_argument('-O', '--output-debug', type=str2bool, nargs='?', const=True, default=False,
                                   help='Normal output generation (validate-hash-compress and UUID file names) '
                                        'or print into the output directory without validation using human-friendly '
                                        'names', metavar='True/False')

    spdict['cleaner'].add_argument('-p', '--run-parallel', type=str2bool, nargs='?', const=True, default=True,
                                   help='Run processing in parallel or all operation must be used sequentially',
                                   metavar='True/False')

    spdict['cleaner'].add_argument('-d', '--with-specific-dicts', dest='w_specific_dicts', type=str2bool, nargs='?',
                                   const=True, default=True, help='Load portal-specific dictionaries (tables)',
                                   metavar='True/False')

    spdict['cleaner'].add_argument('-b', '--with-specific-base-tei', dest='w_specific_tei_base_file', type=str2bool,
                                   nargs='?', const=True, default=True, help='Load portal-specific base TEI XML',
                                   metavar='True/False')

    spdict['inventory-maker'].add_argument('-t', '--task-name', type=str, default='Tag Inventory Maker',
                                           help='The name of the task to appear in the logs', metavar='TASK_NAME')
    spdict['inventory-maker'].add_argument('-r', '--recursive', type=str2bool, nargs='?', const=True, default=True,
                                           help='Use just direct descendants or all', metavar='True/False')

    spdict['bigram-maker'].add_argument('-t', '--task-name', type=str, default='Tag Bigrams Maker',
                                        help='The name of the task to appear in the logs', metavar='TASK_NAME')
    spdict['bigram-maker'].add_argument('-r', '--recursive', type=str2bool, nargs='?', const=True, default=True,
                                        help='Use just direct descendants or all', metavar='True/False')

    spdict['content-tree'].add_argument('-t', '--task-name', type=str, default='HTML Content Tree',
                                        help='The name of the task to appear in the logs', metavar='TASK_NAME')

    # A totally different subparser
    p = subparsers.add_parser('diff-tables', help='Diff Tag Tables')
    p.add_argument('--diff-dir', type=str, help='The directory which contains the directories', metavar='DIR',
                   required=True)
    p.add_argument('--old-filename', type=str, help='The filename for the old table', metavar='FILE', required=True)
    p.add_argument('--new-filename', type=str, help='The filename for the new table', metavar='FILE', required=True)
    p.add_argument('--merge-filename', type=str, help='The filename for the merged table', metavar='FILE',
                   required=True)

    args = vars(parent_parser.parse_args())

    command = args.pop('command')
    if command in command_dict:
        common_args = [args.pop(key) for key in common_params.keys()]
        run_main(*common_args[:-1], command_dict[command][0], args, logfile_level=common_args[-1],
                 console_level=common_args[-1])
    elif command == 'diff-tables':
        diff_all_tag_table(args['diff_dir'], args['old_filename'], args['new_filename'], args['merge_filename'])
    else:
        parent_parser.print_help()
        exit(1)


if __name__ == '__main__':
    entrypoint()
