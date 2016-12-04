.. highlight:: shell

============
Contributing
============

Contributions are welcome, and they are greatly appreciated! Every
little bit helps, and credit will always be given.

You can contribute in many ways:

Types of Contributions
----------------------

Report Bugs
~~~~~~~~~~~

If you run into problems, make sure you are running the latest image and run
it with :envvar:`DEBUG` set to ``true``.

Report bugs at https://github.com/funkyfuture/deck-chores/issues.

If you are reporting a bug, please include:

* Your operating system name and version.
* Your used Docker version.
* Any details about your local setup that might be helpful in troubleshooting.
* Detailed steps to reproduce the bug.

Fix Bugs
~~~~~~~~

Look through the GitHub issues for bugs. Anything tagged with "bug"
and "help wanted" is open to whoever wants to implement it.

Implement Features
~~~~~~~~~~~~~~~~~~

Look through the GitHub issues for features. Anything tagged with "enhancement"
and "help wanted" is open to whoever wants to implement it.

Submit Feedback
~~~~~~~~~~~~~~~

The best way to send feedback is to file an issue at https://github.com/funkyfuture/deck-chores/issues.

If you are proposing a feature:

* Explain in detail how it would work.
* Keep the scope as narrow as possible, to make it easier to implement.
* Remember that this is a volunteer-driven project, and that contributions
  are welcome :)

Get Started!
------------

Ready to contribute? Here's how to set up `deck-chores` for local development.

1. Fork_ the `deck-chores` repo on GitHub.
2. Clone your fork locally::

    $ git clone git@github.com:your_name_here/deck-chores.git

3. Install your local copy into a virtualenv. Assuming you have pew_ installed, this is how you set up your fork for local development::

    $ cd deck-chores
    $ pew new -p $(which python) -a $(pwd) deck-chores
    $ python setup.py develop

4. Create a branch for local development::

    $ git checkout -b name-of-your-bugfix-or-feature

   Now you can make your changes locally.

5a. When you're done making changes, check that your changes pass flake8 and the tests::

    $ tox


   To get flake8 and pytest, just pip install them into your virtualenv.

5b. If you want to run a container for testing purposes::

    $ make run-dev

6. Commit your changes and push your branch to GitHub::

    $ git add .
    $ git commit -m "Your detailed description of your changes."
    $ git push

7. Submit a pull request through the GitHub website.

Pull Request Guidelines
-----------------------

Before you submit a pull request, check that it meets these guidelines:

1. The pull request should include tests.
2. If the pull request adds functionality, the docs should be updated.


.. _Fork: https://github.com/funkyfuture/deck-chores/fork
.. _pew: https://github.com/berdario/pew
