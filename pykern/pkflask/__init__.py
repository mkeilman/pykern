# -*- coding: utf-8 -*-
u"""Flask interface

:copyright: Copyright (c) 2017 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkcollections
from pykern import pkconfig
from pykern import pkio
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp
import beaker.middleware
import flask
import flask.sessions
import py.path
import sys
import werkzeug.exceptions


#: Flask app instance, must be bound globally
app = None

#: Class which is called with exceptions
_EXCEPTIONS_COMPONENT = 'pkbasic'

#: where users live under db_dir
_BEAKER_DATA_DIR = 'beaker/data'

#: Beaker lock db_dir
_BEAKER_LOCK_DIR = 'beaker/lock'

#: What's the key in environ for the session
_ENVIRON_KEY_BEAKER = 'beaker.session'

#: Identifies the user in the Beaker session
_SESSION_KEY_USER = 'uid'

#: Name of component methods
_URI_FUNC_PREFIX = 'uri_'

#: Identifies the user in uWSGI logging (read by uwsgi.yml.jinja)
_UWSGI_LOG_KEY_USER = 'pkflask_user'

#: WSGIApp instance (see `init_by_server`)
_wsgi_app = None

_components = None

_uris = None

def init(uwsgi=None):
    """Initialize globals and populate db dir"""
    global _wsgi_app, app

    assert not app, \
        'already initialized'
    app = _Flask(
        __name__,
        static_folder=None,
        template_folder=None,
    )
    app.config.update(
        PROPAGATE_EXCEPTIONS=True,
    )
    _wsgi_app = _WSGIApp(app, uwsgi)
    _BeakerSession().pkflask_init_app(app, cfg.db_dir)
    app.add_url_rule('/<path:path>', '_dispatch', _dispatch_uri, methods=('GET', 'POST'))
    app.add_url_rule('/', '_dispatch_empty', _dispatch_empty, methods=('GET', 'POST'))
    _init_components(app)
    return app


def session_user(*args, **kwargs):
    """Get/set the user from the Flask session

    With no positional arguments, is a getter. Else a setter.

    Args:
        user (str): if args[0], will set the user; else gets
        checked (bool): if kwargs['checked'], assert the user is truthy
        environ (dict): session environment to use instead of `flask.session`

    Returns:
        str: user id
    """
    environ = kwargs.get('environ', None)
    session = environ.get(_ENVIRON_KEY_BEAKER) if environ else flask.session
    if args:
        session[_SESSION_KEY_USER] = args[0]
        _wsgi_app.set_log_user(args[0])
    res = session.get(_SESSION_KEY_USER)
    if not res and kwargs.get('checked', True):
        raise KeyError(_SESSION_KEY_USER)
    return res


class _Flask(flask.Flask):
    pass


class NotFound(Exception):
    """Raised to indicate page not found exception (404)"""
    def __init__(self, log_fmt, *args, **kwargs):
        super(NotFound, self).__init__()
        self.log_fmt = log_fmt
        self.args = args
        self.kwargs = kwargs


class Component(object):
    def __init__(self, name, app):
        self.name = name

    def file_response(self, rel_path):
        """Return a file for this component along load_path

        Args:
            rel_path (str): partial secure path (use secure_path_info)
        """
        #TODO(robnagler) insert md5
        return flask.send_file(
            pkresource.filename_from_load_path(os.path.join(self.name, str(rel_path))),
            conditional=True,
        )

    def empty_response(self):
        return '';

    def parsed_url(self):
        """Wrapper, because urllib will be changing..."""
        import urlparse

        return urlparse.urlparse(flask.request.url_root)

    def secure_path_info(self):
        import os.path
        import werkzeug.utils

        url = self.parsed_url().path
        parts = url.split('/')
        parts.pop(0)
        for p in parts:
            x = werkzeug.utils.secure_filename(p)
            assert x == p, \
                '{}: invalid path info element; secure={} url={} '.format(p, x, url)
        return parts.join('/') if len(parts) else None


class _BeakerSession(flask.sessions.SessionInterface):
    """Session manager for Flask using Beaker.

    Stores session info in files in server.data_dir. Minimal info kept
    in session.
    """
    def __init__(self, app=None):
        if app is None:
            self.app = None
        else:
            self.init_app(app)

    def pkflask_init_app(self, app, db_dir):
        """Initialize cfg with db_dir and register self with Flask

        Args:
            app (flask): Flask application object
            db_dir (py.path.local): db_dir passed on command line
        """
        app.pkflask_db_dir = db_dir
        data_dir = db_dir.join(_BEAKER_DATA_DIR)
        pkio.mkdir_parent(data_dir)
        lock_dir = data_dir.join(_BEAKER_LOCK_DIR)
        pkio.mkdir_parent(lock_dir)
        sc = {
            'session.auto': True,
            'session.cookie_expires': False,
            'session.type': 'file',
            'session.data_dir': str(data_dir),
            'session.lock_dir': str(lock_dir),
        }
        #TODO(robnagler) Generalize? seems like we'll be shadowing lots of config
        for k in cfg.beaker_session:
            sc['session.' + k] = cfg.beaker_session[k]
        app.wsgi_app = beaker.middleware.SessionMiddleware(app.wsgi_app, sc)
        app.session_interface = self

    def open_session(self, app, request):
        """Called by flask to create the session"""
        return request.environ[_ENVIRON_KEY_BEAKER]

    def save_session(self, *args, **kwargs):
        """Necessary to complete abstraction, but Beaker autosaves"""
        pass


class _WSGIApp(object):
    """Wraps Flask's wsgi_app for logging

    Args:
        app (Flask.app): Flask application being wrapped
        uwsgi (module): `uwsgi` module passed from ``uwsgi.py.jinja``
    """
    def __init__(self, app, uwsgi):
        self.app = app
        # Is None if called from pkcli.service.http or FlaskClient
        self.uwsgi = uwsgi
        self.wsgi_app = app.wsgi_app
        app.wsgi_app = self

    def set_log_user(self, user):
        if self.uwsgi:
            log_user = 'li-' + user if user else '-'
            # Only works for uWSGI (service.uwsgi). For service.http,
            # werkzeug.serving.WSGIRequestHandler.log hardwires '%s - - [%s] %s\n',
            # and no point in overriding, since just for development.
            self.uwsgi.set_logvar(_UWSGI_LOG_KEY_USER, log_user)

    def __call__(self, environ, start_response):
        """An "app" called by uwsgi with requests.
        """
        self.set_log_user(session_user(checked=False, environ=environ))
        return self.wsgi_app(environ, start_response)


@pkconfig.parse_none
def _cfg_db_dir(value):
    """Config value or root_pkg_name or cwd with _DEFAULT_SUBDIR"""
    if value:
        return pkio.py_path(value)
    d = pkio.py_path(pkconfig.root_package().__file__).dirname
    root = pkio.py_path(d).dirname
    # Check to see if we are in our dev directory. This is a hack,
    # but should be reliable.
    if not root.join('requirements.txt').check():
        # Don't run from an install directory
        root = pkio.py_path()
    value = root.join(_DEFAULT_DB_SUBDIR)
    return value


@pkconfig.parse_none
def _cfg_session_secret(value):
    """Reads file specified as config value"""
    if not value:
        return 'dev dummy secret'
    with open(value) as f:
        return f.read()


def _dispatch_uri(path):
    """Called by Flask and routes the base_uri with parameters

    Args:
        path (str): what to route

    Returns:
        Flask.response
    """
    import werkzeug.exceptions
    try:
        if path is None:
            return components[_EXCEPTIONS_COMPONENT].exception_uri_empty()
        return _uri_to_func(path)()
    except NotFound as e:
        return components[_EXCEPTIONS_COMPONENT].exception_not_found(exception=e)
    except Exception as e:
        return components[_EXCEPTIONS_COMPONENT].exception_error(exception=e)


def _dispatch_empty():
    """Hook for '/' route"""
    return _dispatch(None)


def _init_components(app):
    global _components
    global _exceptions
    global _uris
    assert not _components
    _components = pkcollections.Dict()
    _uris = pkcollections.Dict()
    modules = pkconfig.all_modules_in_load_path()
    for k in sorted(modules.keys()):
        m = modules[k]
        for nc, c in inspect.getmembers(OptionParser, predicate=inspect.isclass):
            if not issubclass(c, Component):
                continue
            assert not k in components, \
                '{}: duplicate Component; new={} first={}'.format(
                    k,
                    inspect.getsourcefile(m),
                    inspect.getsourcefile(components[k]),
                )
            components[k] = c(name=k, app=app)
            for nf, f in inspect.getmembers(components[k], predicate=inspect.ismethod):
                if nf.startswith(_URI_FUNC_PREFIX):
                    assert not nf in uris, \
                        '{}: duplicate uri; new={}, first={}'.format(
                            nf,
                            inspect.getsourcefile(f),
                            inspect.getsourcefile(components[k]),
                        )
                    uris[nf[len(_URI_FUNC_PREFIX):]] = f
    assert _EXCEPTIONS_COMPONENT in _components, \
        '{}: component module must exist'.format(_EXCEPTIONS_COMPONENT)


def _uri_to_func(uri):
    first = uri.split('/')[0]
    n = re.sub(r'\W', '_', first).lower()
    try:
        return _uris[n]
    except KeyError:
        return components[_EXCEPTIONS_COMPONENT].exception_uri_not_found


cfg = pkconfig.init(
    beaker_session=dict(
        key=(pkconfig.root_pkg_name() + '_' + pkconfig.cfg.channel, str, 'Beaker: Name of the cookie key used to save the session under'),
        secret=(None, _cfg_session_secret, 'Beaker: Used with the HMAC to ensure session integrity'),
        secure=(False, bool, 'Beaker: Whether or not the session cookie should be marked as secure'),
    ),
    db_dir=(None, _cfg_db_dir, 'where (beaker) database resides'),
)
