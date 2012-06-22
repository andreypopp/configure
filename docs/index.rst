.. configure documentation master file, created by
   sphinx-quickstart on Fri Jun 22 02:03:04 2012.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Configure
=========

Configure is a thin wrapper around PyYAML which extends already readable and
powerful YAML with inheritance, composition and so called object-graph
configuration features.

Basic usage
-----------

Configure uses YAML as a configuration format so you can refer to `YAML
specification`_ for details of how you can compose your configuration. The
basics are the following -- you compose your config as a mapping, which allows
nesting and also can contain sequences::

    # my.conf
    database: postgresql://localhost/dbname
    timeout: !timedelta 10m
    messages:
      - msg: Hello, world!
        author: Andrey Popp
      - msg: Wow!
        author: John Doe
    EOF

Inline comments are started with ``#`` (sharp). To read configuration::

    from configure import Configuration
    config = Configuration.from_file('./my.conf').configure()
    assert config.database == 'postgresql://localhost/dbname'
    assert config['database'] == 'postgresql://localhost/dbname'
    assert config.timeout == datetime.timedelta(seconds=600)

As you can see ``timeout`` value automatically parsed and converted to
``datetime.timedelta`` object by annotating configuration value with
``!timedelta`` tag. There's also ``!re`` builtin tag which passes value to
``re.compile()`` function.

.. note::
   You should always call :meth:`Configuration.configure` method before using
   ``Configuration``.

Objects of class ``Configuration`` implement ``collections.MutableMapping``
interface, but as you already saw, you can also access values by attribute.

.. _YAML specification: http://yaml.org/spec/

Composition
-----------

You can compose configuration from different sources by using ``!include`` tag,
the configuration you included will be inplace of the element you tagged::

    # common.conf
    db: postgresql://localhost/dbname

    # app.conf
    common: !include:common.conf

Note that filename resolves relative to dirname of configuration which contain
``!include`` tag, so in example above ``app.conf`` and ``common.conf`` should be
placed in the same directory. After loading ``app.conf`` configuration::

    config = Configuration.from_file('app.conf').configure()
    assert config.common.db == 'postgresql://localhost/dbname'

You can use ``!include`` tag at any level of the document.

Inheritance
-----------

Configuration can be also composed using inheritance mechanism using
``!extends`` tag. It can be useful for providing some sensible defaults for
configuration file::

    # base.conf
    db: postgresql://localhost/dbname

    # app.conf
    --- !extends:base.conf
    timeout: !timedelta 10m

Filename resolution performs the same like with ``!include`` tag, so
``base.conf`` and ``app.conf`` should be placed in the same directory again.
When you load ``app.conf``::

    config = Configuration.from_file('app.conf').configure()
    assert config.db == 'postgresql://localhost/dbname'

you will see that ``config.db`` was inherited from ``base.conf``. Inheritance
mechanism can also be applied at any level not necessary at the entire
configuration file.

Object-graph configuration
--------------------------

There is also another useful feature ``configure`` library provides -- so called
*object-graph configuration*. Suppose you have somewhere in your code function
which accepts some configuration values and performs some task to configure your
system based on these values::

    # myapp.py
    def configure_db(uri, echo=False):
      ...

You can ask ``configure`` to call this function for you automatically with some
values from configuration::

    # my.conf
    db: !factory:myapp.configure_db
      uri: !ref:dburi
      echo: false

    dburi: postgresql://localhost/dbname

You see there are ``!ref`` and ``!factory`` tags -- first one just references
some other value from configuration which allows you to stay DRY, while
``!factory`` tag call specified function using arguments provided in mapping.

.. note::
   This does work only with positional and keyword arguments and doesn't work
   with "magic" ``*args`` and ``**kwargs`` at the moment.

Another useful tag is the ``!obj`` tag which just imports some python object for
you::

    resource_cls: !obj:myapp.resource.Resource

will import ``myapp.resource.Resource`` object and assign it ``resource_cls``
key.

API reference
-------------

.. automodule:: configure
   :members:
