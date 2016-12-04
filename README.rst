Deck Chores
===========

.. image:: https://img.shields.io/pypi/v/deck_chores.svg
        :target: https://pypi.python.org/pypi/deck_chores

.. image:: https://readthedocs.org/projects/deck-chores/badge/?version=latest
        :target: https://deck-chores.readthedocs.io/en/latest/?badge=latest
        :alt: Documentation Status


Job scheduler for Docker containers, configured via container labels.


* Free software: ISC license
* Documentation: https://deck-chores.readthedocs.io.


Features
--------

- define regular jobs by defining container labels
- use date, interval and cron-like triggers
- set a maximum of simultaneously running instances per job


Example
-------

* TODO


Acknowledgements
----------------

* TODO


Roadmap
-------

0.1
...

- configurable logformat
- take compose projects into account
- also parse image's labels
  - omit when magic label is set
- detect other running deck-chores containers and exit if positive


0.2
...

- parse time units for interval triggers
- handle a global limit on concurrent jobs
- print jobs when receiving SIGHUP
- randomization of interval triggered events
- maybe add a randomize expression for cron triggers


0.3
...

- keep output of job executions
- a rudimentary web ui


Authors
-------

- Frank Sachsenheim (maintaining)
