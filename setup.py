#!/usr/bin/env python

from os import chdir, getcwd
from pathlib import Path
from setuptools import setup
from sys import version_info


if version_info < (3, 7):
    raise RuntimeError("Requires Python 3.7 or later.")


VERSION = '0.3-rc1'

_old_cwd = getcwd()
chdir(Path(__file__).parent)

with open('README.rst') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read()


setup(
    name='deck-chores',
    version=VERSION,
    description="Job scheduler for Docker containers, configured via container labels.",
    long_description=readme + '\n\n' + history,
    author="Frank Sachsenheim",
    author_email='funkyfuture@riseup.net',
    url='https://github.com/funkyfuture/deck-chores',
    packages=['deck_chores'],
    package_dir={'deck_chores': 'deck_chores'},
    include_package_data=True,
    install_requires=[
        'APScheduler~=3.5',
        'cerberus~=1.2',
        'docker~=3.5',
        'fasteners~=0.14',
    ],
    license="ISC license",
    zip_safe=False,
    keywords=['docker', 'cron', 'scheduler', 'jobs', 'labels', 'metadata'],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: ISC License (ISCL)',
        'Natural Language :: English',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: Implementation :: CPython',
    ],
    entry_points={'console_scripts': ['deck-chores = deck_chores.main:main']},
)

chdir(_old_cwd)
