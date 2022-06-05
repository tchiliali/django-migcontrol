Migration Control website
=========================

This website is based on:

* Django
* Wagtail

Development
-----------

To get started, run the following commands:

.. code-block:: console

    # Create a virtualenv and activate it
    # (remember to always activate it when you run commands)
    python3 -m venv .virtualenv
    source .virtualenv/bin/activate

    # Install dependencies
    pip install -r requirements.txt

    # Run migrations (creates the SQLite development database)
    # Remember to always run this step when migrations change
    python manage.py migrate

    # Run the development webserver
    python manage.py runserver

Once the local webserver is running, you can access the website on
``http://localhost:8000``.

In order to have an administrator (superuser) account, run the following command:

.. code-block:: console

    # Create a superuser account
    python manage.py createsuperuser


If you want to make usage of virtualenvs smoother, consider installing
`virtualenv-wrapper <https://virtualenvwrapper.readthedocs.io/en/latest/>`__

Development next steps
----------------------

After you have the site running, you should install
`pre-commit <https://pre-commit.com/>`__ before further changes. Once again,
make sure that your virtualenv is active and then run:

.. code-block:: console

    pip install pre-commit
    pre-commit install

Nothing will happen after this, but in the future your git commits will be
verified locally.


Importing old Wordpress data
----------------------------

The import management command will be adapted to accommodate various types of
dumps from the previous Wordpress site.

Here is an example to import an XML dump of the German Wordpress BoBusi data:

.. code-block:: console

    python manage.py wordpress_to_wagtail --use-wagtail-locale --locale de --app archive --index-model ArchiveIndexPage --post-model ArchivePage /path/to/archives_dump.xml archive

Or for blog posts:

.. code-block:: console

    python manage.py wordpress_to_wagtail --use-wagtail-locale --locale en --app blog --index-model BlogIndexPage --post-model BlogPage /path/to/posts_dump.xml blog

After importing stuff, you can make the new pages ready for translation by synchronizing between mapped languages:

.. code-block:: console

    python manage.py sync_locale_trees


Right-To-Left notes
-------------------

We create an RTL version of the final bootstrap artifact quite manually:

1. Copy the latest generated version of ``main.css`` to ``/css/input.css``.
2. Run ``docker build -f Dockerfile_rtlcss -t rtlcss:latest .``
3. Run ``docker run --volume $PWD/css:/css rtlcss:latest``
4. Copy outputs ``cp css/output.min.css migcontrol/static/css/main.rtl.min.css``
