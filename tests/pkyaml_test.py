# -*- coding: utf-8 -*-
u"""PyTest for :mod:`pykern.pkyaml`

:copyright: Copyright (c) 2015 Bivio Software, Inc.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function, unicode_literals
from io import open

import pytest

import py

from pykern import pkunit
from pykern import pkyaml


def test_load_file():
    """Test values are unicode"""
    y = pkyaml.load_file(pkunit.data_dir().join('conf1.yml'))


def _assert_unicode(value):
    if isinstance(value, dict):
        for k, v in value.items():
            # TODO(robnagler) breaks with PY3
            assert isinstance(k, unicode), \
                '{}: key is not unicode'.format(k)
            _assert_unicode(v)
    elif isinstance(value, list):
        for v in value:
            _assert_unicode(v)
    elif type(value) == str:
        assert isinstance(value, unicode), \
            '{}: value is not unicode'.format(value)