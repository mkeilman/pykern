# -*- coding: utf-8 -*-
u"""pkflask required component

:copyright: Copyright (c) 2017 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkflask
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp
import werkzeug.exceptions


class Component(pkflask.Component):
    """Common uri handlers and exceptions
    """
    def __init__(self):
        super(Component, self).__init__()
        from pykern import pkapi
        pkapi.init()
        self.__pkapi = pkapi

    def exception_error(self, **kwargs):
        import flask

        e = kwargs['exception']
        stack = pkdexc()
        pkdlog('{}: error: url={}; stack:{}', e, flask.request.url, stack)
        werkzeug.exceptions.abort(500)

    def exception_uri_empty(self, **kwargs):
        #TODO(robnagler) need to return a home page
        return self.empty_response()

    def exception_not_found(self, **kwargs):
        from pykern.pkdebug import pkdlog

        e = kwargs['exception']
        pkdlog(e.log_fmt, *e.args, **e.kwargs)
        werkzeug.exceptions.abort(404)

    def exception_uri_not_found(self, **kwargs):
        import flask

        raise pkflask.NotFound('{}: unmapped URI', flask.request.url)

    def uri_favicon_ico(self):
        #TODO(robnagler) return an ico
        return self.empty_response()

    def uri_robots_txt(self):
        #TODO(robnagler) return robots.txt
        return self.empty_response()

    def uri_f(self):
        from pykern import pkresource
        p = self.secure_path_info().split('/', 1)
        if len(p) < 2:
            raise pkflask.NotFound('{}: uri is too short, missing components', p)
        return self.find_component(p[0]).file_response(p[1])


    def uri_1(self):
        """api dispatcher
        """
        return self.__pkapi.dispatch(req)
