History
-------

0.2-rc2 (2017-08-05)
~~~~~~~~~~~~~~~~~~~~

* *changed*: arm builds base on `arm32v6/python <https://hub.docker.com/r/arm32v6/python/>`_
* *changed*: therefore ``arm32v6`` replaces the ``arm``-suffix in image tags
* *changed*: there are no more images that get tagged with ``latest-$architecture``

0.2-rc1 (2017-07-01)
~~~~~~~~~~~~~~~~~~~~

* *refactoring*: uses the Python Docker SDK 2 (#14)
* *removed*: ``ASSERT_FINGERPRINT`` environment variable
* *renamed*: ``DOCKER_DAEMON`` to ``DOCKER_HOST`` to comply with the SDK
* *fix*: check on fixed labels (#18 by @aeri4list)
* documentation updates


0.1 (2017-03-02)
~~~~~~~~~~~~~~~~

* *fix*: docker-py returns ``None`` for labels of images that were created with
  older Docker versions (#7)

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
