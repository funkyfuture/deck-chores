deck-chores
===========

** A job scheduler for Docker containers, configured via container labels.**

* Documentation: http://deck-chores.rtfd.io
* Free software: ISC license


Features
--------

- define regular jobs to run within a container context with container and optionally with image
  labels
- use date, interval and cron-like triggers
- set a maximum of simultaneously running instances per job
- restrict job scheduling to one container per service


Example
-------

Let's say you want to dump the database of a Wordpress once a day. Here's a ``docker-compose.yml``
that defines a job that will be handled by *deck-chores*:

.. code-block:: yaml

    version: '2'

    services:
      wordpress:
        image: wordpress
      mysql:
        image: mariadb
        volumes:
          - ./database_dumps:/dumps
        labels:
          deck-chores.dump.command: sh -c "mysqldump --all-databases > /dumps/dump-$$(date -Idate)"
          deck-chores.dump.interval: daily

It is however recommended use scripts with a proper shebang for such actions. Their outputs to
``stdout`` and ``stderr`` as well as their exit code will be logged by *deck-chores*.


Acknowledgements
----------------

It wouldn't be as charming to write this piece of software without these projects:

* `APScheduler <https://apscheduler.readthedocs.io>`_ for managing jobs
* `cerberus <http://python-cerberus.org>`_ for processing metadata
* `docker-py <https://docker-py.readthedocs.io>`_ for Docker interaction
* `flake8 <http://flake8.pycqa.org/>`_, `mypy <http://mypy-lang.org>`_,
  `pytest <http://pytest.org>`_ and `tox <https://tox.readthedocs.io>`_ for testing
* `Python <https://python.org>`_


Roadmap
-------

0.1
...

- also parse image's labels
  - omit when magic label is set


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
