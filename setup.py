#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup

with open('README.rst') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read()


setup(
    name='deck_chores',
    version='0.1.0',
    description="Job scheduler for Docker containers, configured via container labels.",
    long_description=readme + '\n\n' + history,
    author="Frank Sachsenheim",
    author_email='funkyfuture@riseup.net',
    url='https://github.com/funkyfuture/deck_chores',
    packages=['deck_chores',],
    package_dir={'deck_chores': 'deck_chores'},
    include_package_data=True,
    install_requires=['APScheduler', 'cerberus', 'docker-py'],
    license="ISC license",
    zip_safe=False,
    keywords=['docker', 'cron', 'scheduler', 'jobs'],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: ISC License (ISCL)',
        'Natural Language :: English',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: Implementation :: CPython'
    ],
    entry_points="""
    [console_scripts]
    deck-chores=deck_chores.main:main
    """
)
