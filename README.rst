deck-chores
===========

.. image:: https://img.shields.io/docker/pulls/funkyfuture/deck-chores.svg
        :target: https://hub.docker.com/r/funkyfuture/deck-chores/

.. image:: https://images.microbadger.com/badges/image/funkyfuture/deck-chores.svg
        :target: https://microbadger.com/images/funkyfuture/deck-chores

.. image:: https://img.shields.io/pypi/v/deck-chores.svg
        :target: https://pypi.org/project/deck-chores/

**A job scheduler for Docker containers, configured via container labels.**

* Documentation: https://deck-chores.readthedocs.io
* Image repositories:
    * https://github.com/funkyfuture/deck-chores/pkgs/container/deck-chores
    * https://hub.docker.com/r/funkyfuture/deck-chores
* Code repository: https://github.com/funkyfuture/deck-chores
* Issue tracker: https://github.com/funkyfuture/deck-chores/issues
* Free software: ISC license


Features
--------

- define regular jobs to run within a container context with container and optionally with image
  labels
- use date, interval and cron-like triggers
- set a maximum of simultaneously running instances per job
- restrict job scheduling to one container per service
- multi-architecture image supports ``amd64``, ``arm64`` and ``arm`` platforms
  (the latter are currently not provided for download)


Example
-------

Let's say you want to dump the database of a Wordpress once a day. Here's a ``docker-compose.yml``
that defines a job that will be handled by *deck-chores*:

.. code-block:: yaml

    version: "3.7"

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

It is however recommended to use scripts with a proper shebang for such actions. Their outputs to
``stdout`` and ``stderr`` as well as their exit code will be logged by *deck-chores*.


Maintenance
-----------

The final release is supposed to receive monthly updates that includes updates
of all updateable dependencies. If one is skipped, don't worry. When a second
maintenance release is skipped, feel free to open an issue to ask what the
status is.

You can always build images upon an up-to-date base image with::

    make build


Limitations
-----------

When running on a cluster of `Docker Swarm <https://docs.docker.com/engine/swarm/>`_
nodes, each ``deck-chores`` instance can only observe the containers on the
node it's running on, and hence only restrict to run one job per service within
the node's context.


Acknowledgements
----------------

It wouldn't be as charming to write this piece of software without these projects:

* `APScheduler <https://apscheduler.readthedocs.io>`_ for managing jobs
* `cerberus <http://python-cerberus.org>`_ for processing metadata
* `docker-py <https://docker-py.readthedocs.io>`_ for Docker interaction
* `flake8 <http://flake8.pycqa.org/>`_, `mypy <http://mypy-lang.org>`_,
  `pytest <http://pytest.org>`_ and `tox <https://tox.readthedocs.io>`_ for testing
* `Python <https://www.python.org>`_


Authors
-------

- Frank Sachsenheim (maintaining)
- aeri4list
- alpine-digger
- Brynjar Smári Bjarnason
- Garret Hohmann
