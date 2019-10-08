from pathlib import Path
from setuptools import setup


PROJECT_FOLDER = Path(__file__).parent.resolve()
VERSION = "1.0-dev"

setup(
    name='deck-chores',
    version=VERSION,
    description="Job scheduler for Docker containers, configured via container labels.",
    long_description=(PROJECT_FOLDER / "README.rst").read_text()
    + '\n\n'
    + (PROJECT_FOLDER / "HISTORY.rst").read_text(),
    author="Frank Sachsenheim",
    author_email='funkyfuture@riseup.net',
    url='https://github.com/funkyfuture/deck-chores',
    packages=['deck_chores'],
    package_dir={'deck_chores': 'deck_chores'},
    include_package_data=True,
    install_requires=[
        'APScheduler~=3.6',
        'cerberus~=1.3',
        'docker[ssh,tls]~=4.0',
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
