#!/usr/bin/env python3
# -*- coding: utf-8, vim: expandtab:ts=4 -*-

import sys
import setuptools
import importlib.util


def import_pyhton_file(module_name, file_path):
    # Import module from file: https://docs.python.org/3/library/importlib.html#importing-a-source-file-directly
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


with open('README.md') as fh:
    long_description = fh.read()

setuptools.setup(
    name='html2tei',
    # Get version without actually importing the module (else we need the dependencies installed)
    version=getattr(import_pyhton_file('version', 'html2tei/version.py'), '__version__'),
    author='dlazesz, sarkozizsofia',  # Will warn about missing e-mail
    description='Map the HTML schema of portals to valid TEI XML with the tags and structures used in them using'
                'small manual portal-specific configurations',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/ELTE-DH/HTML2TEI',
    # license='GNU Lesser General Public License v3 (LGPLv3)',  # Never really used in favour of classifiers
    # platforms='any',  # Never really used in favour of classifiers
    packages=setuptools.find_packages(exclude=['tests', 'docs']),
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)',
        'Operating System :: POSIX :: Linux',
    ],
    python_requires='>=3.6',
    install_requires=['beautifulsoup4>=4.9.0,<5.0.0', 'justext>=2.2.0,<3.0.0', 'lxml>=4.5.0,<5.0.0',
                      'newspaper3k>=0.2.8,<1.0.0', 'pyyaml>=5.3.0,<6.0.0', 'warcio>=1.7.0,<2.0.0',
                      'webarticlecurator>=1.4.0,<2.0.0'],
    include_package_data=True,
    entry_points={
        'console_scripts': [
            'html2tei=html2tei.__main__:main',
        ]
    },
)
