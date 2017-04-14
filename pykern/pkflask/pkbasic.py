# -*- coding: utf-8 -*-
u"""pkflask required component

:copyright: Copyright (c) 2017 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkflask
import werkzeug.exceptions


class Component(pkflask.Component):
    """Common uri handlers and exceptions
    """
    def __init__(self):
        super(Component, self).__init__()
        from pykern import pkapi
        pkapi.init()
        self.__pkapi = pkapi


    def uri_favicon_ico(self, req):
        return self.empty_response()

    def uri_robots_txt(self, req):
        return self.empty_response()

    def uri_v1(self, req):
        """api dispatcher
        """
        return self.__pkapi.dispatch(req)

    def exception_empty_uri(self, req):
        return self.empty_response()

    def exception_uri_not_found(self, req):
        werkzeug.exceptions.abort(404)

    def exception_not_found(self, req):
        werkzeug.exceptions.abort(404)
