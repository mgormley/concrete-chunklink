#!/usr/bin/env python
#
# Example usage
#   python setup.py install
#

from setuptools import setup

setup(
    name='concrete_chunklink',
    version='0.1',
    description='Wrapper of the chunklink.pl script used by CoNLL-2000 for use on Concrete Communications.',
    author='Matt Gormley',
    author_email='mrg@cs.jhu.edu',
    url='http://www.cs.jhu.edu/~mrg/',
    packages=['concrete_chunklink'],
    install_requires = ['concrete>=4.4.0<4.8.0'],
    entry_points={
        'console_scripts': [
            'add_chunks = concrete_chunklink:main',
        ],
    })
