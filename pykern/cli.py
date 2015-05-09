# -*- coding: utf-8 -*-
"""Invoke commands from command line interpreter modules.

Any module in ``<root_pkg>.b_cli`` will be found by this module. The
public functions of the module will be executed when called from the
command line. This module is invoked by :mod:`pykern.pykern_console`.
Every project must have its own invocation module.

The basic form is: <project> <simple-module> <function>. <simple-module>
is the module without `<root_pkg>.b_cli`.  <function> is any function
that begins with a letter and contains word characters (\w).

If the module only has one public function named default_command,
the form is: <project> <simple-module>.

The purpose of this module is to simplify command-line modules. There is
no boilerplate. You just create a module with public functions
in a particular package location (e.g. `pykern.b_cli`).
This module does the rest.

Example:
    If you are in project ``foobar``, you would create
    a ``foobar_console.py``, which would contain::

    import sys

    import pykern.cli


    def main():
        return pykern.cli.main('foobar')


    if  __name__ == '__main__':
        sys.exit(main())

    To invoke :func:`foobar.b_cli.projex.snafu` command,
    you run the following from the command line::

        foobar projex snafu

    This module uses :mod:`argh` so cli modules can specify arguments and
    such as follows::

        @argh.arg('greet', default='hello world', nargs='+', help='salutation')
        def func(greet):

    If you are using Python 3, you can say::

        def func(greet : 'salutation')

:copyright: Copyright (c) 2015 Bivio Software, Inc.  All Rights Reserved.
:license: Apache, see LICENSE for more details.
"""

from __future__ import print_function
from __future__ import absolute_import

import argparse
import importlib
import inspect
import os.path
import pkgutil
import sys

import argh

#: Sub-package to find command line interpreter (cli) modules will be found
CLI_PKG = 'b_cli'

#: If a module only has one command named this, then execute directly.
DEFAULT_COMMAND = 'default_command'


def main(root_pkg, argv=None):
    """Invokes module functions in :mod:`pykern.b_cli`

    Looks in ``<root_pkg>.b_cli`` for the ``argv[1]`` module. It then
    invokes the ``argv[2]`` method of that module.

    Args:
        root_pkg (str): top level package name
        argv (list of str): Defaults to `sys.argv`. Only used for testing.

    Returns:
        int: 0 if ok. 1 if error (missing command, etc.)
    """
    if not argv:
        argv = list(sys.argv)
    prog = os.path.basename(argv.pop(0))
    if len(argv) == 0:
        return _list_all(root_pkg, prog)
    module_name = argv.pop(0)
    cli = _module(root_pkg, module_name)
    if not cli:
        return 1
    prog = prog + ' ' + module_name
    parser = argparse.ArgumentParser(
        prog=prog, formatter_class=argh.PARSER_FORMATTER)
    cmds = _commands(cli)
    if len(cmds) == 1 and cmds[0].__name__ == DEFAULT_COMMAND:
        argh.set_default_command(parser, cmds[0])
    else:
        argh.add_commands(parser, cmds)
    argh.dispatch(parser, argv=argv)
    return 0


def _commands(cli):
    """Extracts all public functions from `cli`

    Args:
        cli (module): where commands are executed from

    Returns:
        list of function: public functions sorted alphabetically
    """
    res = []
    for n, t in inspect.getmembers(cli):
        if inspect.isfunction(t):
            res.append(t)
    sorted(res, key=lambda f: f.__name__.lower())
    return res


def _import(root_pkg, name=None):
    """Dynamically imports ``root_pkg.CLI_PKG[.name]``.

    Args:
        root_pkg (str): top level package
        name (str): cli module

    Returns:
        module: imported module

    Raises:
        ImportError: if module could not be loaded
    """
    p = [root_pkg, CLI_PKG]
    if name:
        p.append(name)
    return importlib.import_module('.'.join(p))


def _list_all(root_pkg, prog):
    """Prints a list of importable modules and exits.

    Searches ``<root_pkg>.b_cli` for submodules, and prints their names.

    Args:
        root_pkg (str): top level package
        prog (str): argv[0], name of program invoked

    Returns:
        int: 0 if ok. 1 if error.

    """
    res = []
    b_cli = _import(root_pkg)
    path = os.path.dirname(b_cli.__file__)
    for _, n, ispkg in pkgutil.iter_modules([path]):
        if not ispkg:
            res.append(n)
    sorted(res, key=str.lower)
    res = '\n'.join(res)
    sys.stderr.write(
        'usage: {} module command [args...]\nModules:\n{}\n'.format(prog, res),
    )
    return 1


def _module(root_pkg, name):
    """Imports the module, catching `ImportError`

    Args:
        root_pkg (str): top level package
        name(str): unqualified name of the module to be imported

    Returns:
        module: imported module
    """
    try:
        return _import(root_pkg, name)
    except Exception as e:
        sys.stderr.write(str(e) + "\n")
    return None