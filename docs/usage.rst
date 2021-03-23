Usage
=====

Invocation
----------

On a single host
~~~~~~~~~~~~~~~~

Usually you would run ``deck-chores`` in a container::

    $ docker run --rm -v /var/run/docker.sock:/var/run/docker.sock funkyfuture/deck-chores:1

.. note::

    There's a manifest on the Docker Hub that maps images to builds targeting ``amd64``, ``amd64``
    and ``armv7l`` architectures.
    Thus you don't need to specify any platform indicator, the Docker client will figure out which
    one is the proper image to pull.

Likewise, docker-compose_ can be used with such configuration:

.. code-block:: yaml

    version: "3.7"

    services:
      officer:
        image: funkyfuture/deck-chores:1
        restart: unless-stopped
        environment:
          TIMEZONE: Asia/Tel Aviv
        volumes:
          - /var/run/docker.sock:/var/run/docker.sock


You could also install ``deck-chores`` from the Python Package Index with ``pip`` or ``pipx``
(recommended)::

    $ pipx install deck-chores

and then run it::

    $ deck-chores


Now one instance of ``deck-chores`` is running and will handle all job definitions that it discovers
on containers that run on the Docker host.

In a Docker Swarm
~~~~~~~~~~~~~~~~~

``deck-chores`` can be run in a Docker Swarm cluster, but it must be deployed on all nodes and it
cannot restrict jobs to be run in only one of the containers that manifest a service. This would be
a suitable stack definition:

.. code-block:: yaml

    version: "3.7"

    services:
      officer:
        image: funkyfuture/deck-chores:1
        deploy:
          mode: global
        environment:
          TIMEZONE: Europe/Berlin
          # it isn't guaranteed that service or job options don't override this:
          DEFAULT_FLAGS: noservice
        volumes:
          - /var/run/docker.sock:/var/run/docker.sock


It can be deployed with::

    $ docker stack deploy --compose-file docker-compose.yml deck-chores


Now one instance of ``deck-chores`` is running on each Swarm node and each will handle all job
definitions that it discovers on containers that run on the same Swarm node. No instance is aware
of the events and containers on other nodes.

Caveats & Tips
--------------

.. caution::

    There's yet no way to distinguish container events that happen during an **image build** from
    others (:issue:`6` and `#15211 <docker-issue-15211_>`_). Thus when an image is built,
    `deck-chores` will register and remove jobs on all intermediate containers following labels
    that define jobs.
    It would possibly trigger these jobs, which might lead to a corrupted build.
    You can avoid this risk by building images on a host that is not observed by `deck-chores` or
    by pausing it during image builds. Another alternative could be using Podman_ to build images.

.. _Podman: https://podman.io/


Containers without an enduring main process
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If the container is supposed to only run the scheduled commands and not a main process, use a
non-stopping no-op command as main process like in this snippet of a ``docker-compose.yml`` file:

.. code-block:: yaml

    services:
      neverending:
        # …
        command: tail -f /dev/null
        labels:
          deck-chores.daily_job.command: daily_command …
          deck-chores.daily_job.interval: daily


Making jobs' output available to ``docker logs`` of the executing container
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Docker captures the output of the first process in a container as logged data. In order to capture
the output of a job's command as well, its output needs to be redirected to the main process'
``stdout`` and ``stderr``, e.g. by redirecting a command's output with a shell::

    deck-chores.a_job.command: sh -c "/usr/local/bin/job_script.sh > /proc/1/fd/1 2> /proc/1/fd/2"

The normal behaviour of ``docker logs`` is that it separates ``stdout`` and ``stderr`` into 
different streams for output. If you want to retain this behaviour, you must redirect 
both ``stdout`` (``>``) and ``stderr`` (``2>``) separately as shown.



Listing all registered jobs
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Information, including the next scheduled execution, about the registered jobs of a deck-chores
instance can be logged at once by sending ``SIGUSR1`` signal to the process, e.g. to one that runs
in a container::

    docker kill --signal USR1 <CONTAINER>



Job definitions
---------------

Job definitions are parsed from a container's metadata aka labels. A label's key must be in the
namespace defined by :envvar:`LABEL_NAMESPACE` (default: ``deck-chores``) to be considered. A job
has its own namespace that holds all its attributes. Thus an attribute's key has usually this
schema::

    $LABEL_NAMESPACE.<job name>.<job attribute>

An exception is a job's ``env`` namespace that is structured like this::

    $LABEL_NAMESPACE.<job name>.env.<variable name>

The *job name* ``options`` cannot be used as it is reserved for setting :ref:`options`.

A job name can consist of lower-case letters, digits and dashes.

The following attributes are available:

=========  ====================================================================
Attribute  Description
=========  ====================================================================
command    the command to run
cron       a :ref:`cron` definition
date       a :ref:`date` definition
env        this namespace holds environment variables that are set on the
           command's execution context
interval   an :ref:`interval` definition
jitter     the maximum length of a random delay before each job's execution (in
           conjunction with a :ref:`cron` or :ref:`interval` trigger); can be
           either a number that define seconds or a number with a subsequent
           time unit indicator like the :ref:`interval` trigger
max        the maximum of simultaneously running command instances, defaults to
           :envvar:`DEFAULT_MAX`
timezone   the timezone that the trigger relates to, defaults to
           :envvar:`TIMEZONE`
user       the user to run the command; see :ref:`the user option <options-user>` for details
           regarding the defaults
workdir    the working directory when the command is executed
=========  ====================================================================

The attribute ``command`` and one of ``cron``, ``date`` or ``interval`` are *required* for each
job.

Example snippet from a ``docker-compose.yml`` file:

.. code-block:: yaml

    services:
      web:
        # ...
        labels:
          deck-chores.clear-caches.command: drush cc all
          deck-chores.clear-caches.interval: daily
          deck-chores.clear-caches.user: www-data
          deck-chores.clear-caches.env.ENVIRONMENT: production

Or baked into an image:

.. code-block:: Dockerfile

    LABEL deck-chores.clear-caches.command="drush cc all" \
          deck-chores.clear-caches.interval="daily" \
          deck-chores.clear-caches.user="www-data" \
          deck-chores.clear-caches.env.ENVIRONMENT="production"


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
    * * * * 6 1 0 0    # run every Sunday at 1:00
    6 1 0 0            # as shortened expression
    sun 1 0 0          # as 'speaking' variant
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

This trigger defines a repetition by a fixed interval. It can either be a string where time units
follow numbers or a sequence of numbers that qualify time units by order.

In the first form the numbers can be decimal fractions and the time units are determined by the
first letter of a token as **w**\ eek, **d**\ ay, **h**\ our, **m**\ inute or **s**\ econd.

In the anonymous form the interval is added up by the fields *weeks*, *days*, *hours*, *minutes*
and *seconds* in that order. Possible field separators are ``.``, ``:``, ``/`` and spaces. Missing
fields are filled up with ``0`` on the left.

Examples
........

::

    28 Days       # run every 4 weeks
    4 wookies     # run every 4 weeks
    42s 0.5d      # run every twelve hours and 42 seconds
    42:00:00      # run every fourty-two hours
    100/00:00:00  # run every one hundred days

There are also the convenience shortcuts ``weekly``, ``daily``, ``hourly``, ``every minute`` and
``every second``.

.. note::

    Though it uses the same units of measurement, an interval is different from a recurring point
    in time of a specific calendar system, it describes the time *between* two events. Hence you
    should expect a job that is defined with this type of trigger to run the defined time *after*
    the job has been registered. To define a recurring point in time, see the cron_ trigger.

.. caution::

    Mind that ``deck-chores`` doesn't track jobs' status when they are removed from the scheduler
    and doesn't persist any data between its invocations. Any such event would therefore reset the
    next scheduled run time of a job. Depending on a system's usage this is more or less likely
    to happen. For longer intervals, a cron_ trigger would therefore be preferable.


.. _options:

Container-scoped configuration
------------------------------

.. _options-user:

user
~~~~

A user that shall run *all* jobs for a container can be set with a label name of this form::

    $LABEL_NAMESPACE.options.user

The option can also be defined for an image and is considered when the ``image``
:ref:`flag <options-flags>` is set.
If this option is not set, Docker uses the user that was specified with the ``--user`` option on
container creation or falls back to the one defined in the underlying image.


.. _options-flags:

flags
~~~~~

Option flags control *deck-chores*'s behaviour with regard to the labeled container and override
the setting of :envvar:`DEFAULT_FLAGS`. The schema for a flags label name is::

    $LABEL_NAMESPACE.options.flags

Options are set as comma-separated list of flags. An option set by :envvar:`DEFAULT_FLAGS` can
be unset by prefixing with ``no``.

These options are available:

.. option:: image

    Job definitions in the container's basing image labels are also parsed while container label
    keys override these.

.. option:: service

    Restricts jobs to one container of those that are identified with the same service.

    See :envvar:`SERVICE_ID_LABELS` regarding service identity.


Environment variables
---------------------

deck-chore's behaviour is defined by these environment variables:

.. envvar:: CLIENT_TIMEOUT

    The timeout for responses from the Docker daemon in seconds without unit indicator. The
    default is imported from *docker-py*.

.. envvar:: CONTAINER_CACHE_SIZE

    default: ``128``

    The size of caches that save immutable container properties, like the parsed and possibly
    absent job definitions. Since memory is cheap and so are the stored objects, increase this when
    you have a lot of containers floating around to reduce latency.

.. envvar:: DOCKER_HOST

    default: ``unix://var/run/docker.sock``

    The URL of the Docker daemon to connect to.

.. envvar:: DEBUG

    default: ``no``

    Log debugging messages, enabled by ``on``, ``true`` or ``yes``.

.. envvar:: DEFAULT_FLAGS

    default: ``image,service``

    The default for a job option's :ref:`flags <options-flags>` attribute.

.. envvar:: DEFAULT_MAX

    default: ``1``

    The default for a job's ``max`` attribute.

.. envvar:: JOB_NAME_REGEX

    default: ``[a-z0-9-]+``

    The allowed regex for customized job names.

.. envvar:: JOB_POOL_SIZE

    default: ``10``

    The pool size of job executors defines the maximum number of jobs that can
    run at the same time.

.. envvar:: LABEL_NAMESPACE

    default: ``deck-chores``

    The label namespace to look for job definitions and container options.

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

    Enabled by ``on``, ``true`` or ``yes``.

.. envvar:: SSL_VERSION

    default: ``TLS`` (selects the highest version supported by the client and the daemon)

    For other options see the names provided by Python's ssl_ library prefixed with ``PROTOCOL_``.

Authentication related files are expected to be available at ``/config/ca.pem``,
``/config/cert.pem`` respectively ``/config/key.pem``.


.. _docker-issue-15211: https://github.com/moby/moby/issues/15211
.. _docker-compose: https://docs.docker.com/compose/
.. _log record attributes: https://docs.python.org/3/library/logging.html#logrecord-attributes
.. _ssl: https://docs.python.org/3/library/ssl.html#ssl.PROTOCOL_TLS
