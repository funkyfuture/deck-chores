Usage
=====

Invocation
----------

Usually you would run `deck-chores` in a container::

    $ docker run --rm -v /var/run/docker.sock:/var/run/docker.sock funkyfuture/deck-chores

.. note::

    There's a manifest on the Docker Hub that maps images to builds targeting ``amd64`` and ``arm``
    architectures.
    Thus you don't need to specify any platform indicator, the Docker client will figure out which
    one is the proper image to pull.

Likewise, docker-compose_ can be used with such configuration:

.. code-block:: yaml

    version: '2'

    services:
      officer:
        image: funkyfuture/deck-chores
        restart: unless-stopped
        environment:
          TIMEZONE: Asia/Tel Aviv
        volumes:
          - /var/run/docker.sock:/var/run/docker.sock


You could also install `deck-chores` from the Python Package Index with ``pip`` or ``pipsi``
(recommended)::

    $ pipsi install deck-chores

and then run it::

    $ deck-chores


Now one instance of `deck-chores` is running and will handle all job definitions that it discovers
on containers that run on the Docker host.

Caveats
-------

.. caution::

    There's yet no way to distinguish container events that happen during an **image build** from
    others (#6 and `#15211 <docker-issue-15211_>`_). Thus when an image is built, `deck-chores`
    will register and remove jobs on all intermediate containers following labels that define jobs.
    It would possibly trigger these jobs, which might lead to a corrupted build.
    You can avoid this risk by building images on a host that is not observed by `deck-chores` or
    by pausing it during image builds.


Job definitions
---------------

Job definitions are parsed from a container's metadata aka labels. A label's key must be in the
namespace defined by :envvar:`LABEL_NAMESPACE` (default: ``deck-chores``) to be considered. A job
has an own namespace that holds all its attributes. Thus an attribute's key has this schema::

    $LABEL_NAMESPACE.<job name>.<job attribute>

The *job name* ``options`` cannot be used as it is reserved for setting :ref:`options`.

The following attributes are available:

=========  ========================================================
Attribute  Description
=========  ========================================================
command    the command to run
cron       a :ref:`cron` definition
date       a :ref:`date` definition
interval   a :ref:`interval` definition
max        the maximum of simultaneously running command instances,
           defaults to :envvar:`DEFAULT_MAX`
timezone   the timezone that *cron* and *date* relate to,
           defaults to :envvar:`TIMEZONE`
user       the user to run the command,
           defaults to :envvar:`DEFAULT_USER`
=========  ========================================================

The attribute ``command`` and one of ``cron``, ``date`` or ``interval`` are *required* for each job.

Example snippet from a ``docker-compose.yml`` file:

.. code-block:: yaml

    services:
      web:
        # ...
        labels:
          deck-chores.clear-caches.command: drush cc all
          deck-chores.clear-caches.interval: daily
          deck-chores.clear-caches.user: www-data

Or baked into an image:

.. code-block:: Dockerfile

    LABEL deck-chores.clear-caches.command="drush cc all" \
          deck-chores.clear-caches.interval="daily" \
          deck-chores.clear-caches.user="www-data"


Job triggers
------------

.. _cron:

cron
~~~~

cron triggers allow definitions for repeated run times like for the well-known *cron* daemon.
In contrast to the classic, the sequence of fields is flipped, starting with the greatest unit
on the left. The fields are separated by spaces, missing fields are filled up with ``*`` on the
left.

The fields from left to right define:

  * ``year``
  * ``month``
  * ``day`` (of month)
  * ``week`` (of year)
  * ``day_of_week``
  * ``hour``
  * ``minute``
  * ``second``

See APScheduler's documentation for details on its versatile expressions_.

.. _expressions: https://apscheduler.readthedocs.io/en/latest/modules/triggers/cron.html#expression-types

Examples
........

::

    * * * * * */3 0 0  # run on all hours dividable by 3
    */3 0 0            # as shortened expression
    * * * * 7 1 0 0    # run every Sunday at 1:00
    7 1 0 0            # as shortened expression
    * * * * * 1-4 0 0  # run daily at 1:00, 2:00, 3:00 and 4:00
    1-4 0 0            # as shortened expression

.. _date:

date
~~~~

A one-time trigger that is formatted as ``YYYY-MM-DD [HH:MM:SS]``.

An omitted time is interpreted as ``0:00:00``. Note that times must include a seconds field.

.. _interval:

interval
~~~~~~~~

This trigger defines a repetition by a fixed interval. The interval is added up by the fields
*weeks*, *days*, *hours*, *minutes* and *seconds*. Possible field separators are ``.``, ``:``,
``/`` and spaces. Missing fields are filled up with ``0`` on the left.

Examples
........

::

    42:00:00      # run every fourty-two hours
    100/00:00:00  # run every one hundred days

There are also the convenience shortcuts ``weekly``, ``daily``, ``hourly``, ``every minute`` and
``every second``.

.. _options:

Container options
-----------------

Option flags control *deck-chores*'s behaviour. The schema for an option label name is::

    $LABEL_NAMESPACE.options

Options are set as comma-separated list of flags. An option set by :envvar:`DEFAULT_OPTIONS` can
be unset by prefixing with ``no``.

These options are available:

.. option:: image

    Job definitions in image labels are also parsed while container label keys override these.

.. option:: service

    Restricts jobs to one container of those that are identified with the same service.

    See :envvar:`SERVICE_ID_LABELS` regarding service identity.


Environment variables
---------------------

deck-chore's behaviour is defined by these environment variables:

.. envvar:: CLIENT_TIMEOUT

    The timeout for responses from the Docker daemon. The default is imported from *docker-py*.

.. envvar:: DOCKER_HOST

    default: ``unix://var/run/docker.sock``

    The URL of the Docker daemon to connect to.

.. envvar:: DEBUG

    default: ``no``

    Log debugging messages.

.. envvar:: DEFAULT_MAX

    default: ``1``

    The default for a job's ``max`` attribute.

.. envvar:: DEFAULT_OPTIONS

    default: ``image,service``

    The default for a job's :ref:`options <options>` attribute.

.. envvar:: DEFAULT_USER

    default: ``root``

    The default for a job's ``user`` attribute.

.. envvar:: LABEL_NAMESPACE

    default: ``deck-chores``

    The label namespace to look for job definitions.

.. envvar:: LOG_FORMAT

    default: ``{asctime}|{levelname:8}|{message}``

    Pattern that formats `log record attributes`_.

.. envvar:: SERVICE_ID_LABELS

    default: ``com.docker.compose.project,com.docker.compose.service``

    A comma-separated list of container labels that identify a unique service with possibly multiple
    container instances. This has an impact on how the :option:`service` option behaves.

.. envvar:: TIMEZONE

default: ``UTC``

    The job scheduler's timezone and the default for a job's ``timezone`` attribute.

TLS options
~~~~~~~~~~~

.. envvar:: ASSERT_HOSTNAME

    default: ``no``

.. envvar:: SSL_VERSION

    default: ``TLS`` (selects the highest version supported by the client and the daemon)

    For other options see the names provided by Python's ssl_ library prefixed with ``PROTOCOL_``.

Authentication related files are expected to be available at ``/config/ca.pem``,
``/config/cert.pem`` respectively ``/config/key.pem``.


.. _docker-issue-15211: https://github.com/docker/docker/issues/15211
.. _docker-compose: https://docs.docker.com/compose/
.. _log record attributes: https://docs.python.org/library/logging.html#logrecord-attributes
.. _ssl: https://docs.python.org/library/ssl.html#ssl.PROTOCOL_TLS
