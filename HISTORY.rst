History
-------

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
