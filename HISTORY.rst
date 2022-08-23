History
-------

Maintenance releases are not mentioned here, they update all dependencies and
trigger complete rebuilds of the container images.

1.3 (2022-08-23)
~~~~~~~~~~~~~~~~

* *removed*: the environment variable ``SSL_VERSION`` has no effect and is marked as deprecated

1.2 (2021-06-25)
~~~~~~~~~~~~~~~~

* *new*: the ``STDERR_LEVEL`` environment variable can define log levels whose messages are then
  dumped to stderr instead of stdout
* *new*: the environment variable ``JOB_NAME_REGEX`` can be used to define patterns that job names
  must match

1.0 (2020-03-27)
~~~~~~~~~~~~~~~~

* *new*: maintenance release automation

1.0-rc1 (2020-02-16)
~~~~~~~~~~~~~~~~~~~~

This release candidate for the final version brings improved documentation, logging, a lot of code
cleanup and these notable changes:

* *new*: jobs' container assignments and states are properly adjusted with regards to other
  instances of a service's state
* *new*: ``deck-chores``' cache sizes for container properties can be controlled with
  ``CONTAINER_CACHE_SIZE``
* *new*: the environment variable ``JOB_POOL_SIZE`` can be used to adapt the job executors pool size
* *new*: images are build for ``arm64`` (aka ``aarch64``) architectures

All previously deprecated options have been removed.

0.3.1 (2019-03-02)
~~~~~~~~~~~~~~~~~~

* *fix*: relax interpreter constraint for installations on rtfd.io

0.3 (2019-01-06)
~~~~~~~~~~~~~~~~

* *fix*: log the version at startup, not its variable name

0.3-rc1 (2018-12-18)
~~~~~~~~~~~~~~~~~~~~

* *new*: the container configuration ``options.user`` allows to set an executing user
  for all jobs that don't define one, can also be set on an image (:issue:`5`)
* *new*: environment variables for a job can be set in a job's ``env`` namespace
  (:issue:`41`)
* *new*: a job's ``workdir`` attribute can be used to set the working directory (:issue:`42`)
* *new*: cron and interval triggers can be configured to delay randomly with the ``jitter``
  option (:issue:`43`)
* *new*: interval triggers and the jitter option can be defined with strings containing
  time units
* *removed*: the ``DEFAULT_USER`` environment variable is removed (:issue:`17`)
* *removed*: parsing of environment variables ``ASSERT_FINGERPRINT`` and ``DOCKER_DAEMON``
* *changed*: the container configuration ``options`` is moved to ``options.flags``
* *changed*: the environment variable ``DEFAULT_OPTIONS`` is renamed to ``DEFAULT_FLAGS``
* *changed*: upgraded base image
* *changed*: upgraded used Cerberus version
* *changed*: requires Python 3.7
* *fix*: includes the ``tzdata`` package in the image (:issue:`33`)
* *fix*: add jobs as paused for paused containers on startup
* *refactoring*: uses the Python Docker SDK 3.5 (:issue:`31`)

0.2 (2018-02-23)
~~~~~~~~~~~~~~~~

* *new*: documentation how to run scheduled jobs only (:issue:`25` by @binnisb)
* *fix*: documentation on cron triggers (:issue:`27` by @alpine-digger)

0.2-rc3 (2017-12-23)
~~~~~~~~~~~~~~~~~~~~

* *changed*: arm builds base on `python:3.6-alpine <https://hub.docker.com/_/python/>`_
  that are executed on an ARMv7l architecture
* *changed*: Updated dependencies *APScheduler* and *docker-py*

0.2-rc2 (2017-08-05)
~~~~~~~~~~~~~~~~~~~~

* *changed*: arm builds base on `arm32v6/python <https://hub.docker.com/r/arm32v6/python/>`_
* *changed*: therefore ``arm32v6`` replaces the ``arm``-suffix in image tags
* *changed*: there are no more images that get tagged with ``latest-$architecture``

0.2-rc1 (2017-07-01)
~~~~~~~~~~~~~~~~~~~~

* *refactoring*: uses the Python Docker SDK 2 (:issue:`14`)
* *removed*: ``ASSERT_FINGERPRINT`` environment variable
* *renamed*: ``DOCKER_DAEMON`` to ``DOCKER_HOST`` to comply with the SDK
* *fix*: check on fixed labels (:issue:`18` by @aeri4list)
* documentation updates


0.1 (2017-03-02)
~~~~~~~~~~~~~~~~

* *fix*: docker-py returns ``None`` for labels of images that were created with
  older Docker versions (:issue:`7`)

0.1.beta3 (2017-01-22)
~~~~~~~~~~~~~~~~~~~~~~

* *new*: there's now a build for arm architectures
* *new*: an architecture agnostic manifest is pushed to the image registry for
  release images

0.1.beta2 (2016-12-08)
~~~~~~~~~~~~~~~~~~~~~~

* *new:* set log format per :envvar:LOG_FORMAT
* *new:* an options label to set behavioural flags
* *new:* containers can be identified as a service by configurable labels
* *new:* job definitions for further containers of a service are ignored
  (default, opt-out can be configured)
* *new:* image labels can also be parsed for job definitions
  (default, opt-out can be configured)

0.1.beta1 (2016-12-04)
~~~~~~~~~~~~~~~~~~~~~~

* First release with full documentation
