# -*- coding: utf-8 -*-
u"""pytest for `pykern.pkdebug`

:copyright: Copyright (c) 2015 Bivio Software, Inc.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function, unicode_literals
from io import open

import inspect
import os
import os.path
import pytest
from io import StringIO

# Do not import anything from pk so test_pkdc() can be fresh

def test_pkdc(capsys):
    """Verify basic output"""
    # 3 the pkdc statement is three lines forward, hence +3
    this_file = os.path.relpath(__file__)
    control = this_file + ':' + str(inspect.currentframe().f_lineno + 4) + ':test_pkdc t1'
    os.environ['PYKERN_DEBUG_CONTROL'] = control
    from pykern.pkdebug import pkdc, init, pkdp, _init_from_environ
    _init_from_environ()
    pkdc('t1')
    out, err = capsys.readouterr()
    assert err == control + '\n', \
        'When control exactly matches file:line:func msg, output is same'
    pkdc('t2')
    out, err = capsys.readouterr()
    assert err == '', \
        'When pkdc msg does not match control, no output'
    init('t3')
    pkdc('t3 {}', 'p3')
    out, err = capsys.readouterr()
    assert 'test_pkdc t3' in err, \
        'When control is simple msg match, expect output'
    assert 't3 p3\n' in err, \
        'When positional format *args, expect positional param in output'
    output = StringIO()
    init('t4', output)
    pkdc('t4 {k4}', k4='v4')
    out, err = capsys.readouterr()
    assert 'test_pkdc t4 v4' in output.getvalue(), \
        'When params is **kwargs, value is formatted from params'
    assert err == '', \
        'When output is passed to init(), stderr is empty'


def test_pkdc_dev(capsys):
    """Test max exceptions"""
    import pykern.pkdebug as d
    d.init('.')
    for i in range(d.MAX_EXCEPTION_COUNT):
        d.pkdc('missing format value {}')
        out, err = capsys.readouterr()
        assert 'invalid format' in err, \
            'When fmt is incorrect, output indicates format error'
    d.pkdc('any error{}')
    out, err = capsys.readouterr()
    assert err == '', \
        'When exception_count exceeds MAX_EXCEPTION_COUNT, no output'


def test_init(capsys):
    from pykern import pkunit
    f = pkunit.empty_work_dir().join('f1')
    from pykern.pkdebug import pkdp, init
    init(output=f)
    pkdp('init1')
    out, err = capsys.readouterr()
    assert '' == err, \
        'When output is a file name, nothing goes to err'
    from pykern import pkio
    assert 'init1\n' in pkio.read_text(f), \
        'File output should contain msg'


def test_init_dev(capsys):
    """Test init exceptions"""
    import pykern.pkdebug as d
    output = StringIO()
    d.init(r'(regex is missing closing parent', output)
    out, err = capsys.readouterr()
    assert not d._have_control, \
        'When control re.compile fails, _printer is not set'
    assert 'compile error' in output.getvalue(), \
        'When an exception in init(), output indicates init failure'
    assert err == '', \
        'When an exception in init() and output, stderr is empty'
    d.init(r'[invalid regex', '/invalid/file/path')
    assert not d._have_control, \
        'When invalid control regex, _have_control should be false'
    out, err = capsys.readouterr()
    assert 'compile error' in err, \
        'When exception in init() and output invalid, init failure written to stderr'


def test_pkdi(capsys):
    """Basic output and return with `pkdi`"""
    from pykern.pkdebug import pkdi, init
    init()
    assert 333 == pkdi(333)
    out, err = capsys.readouterr()
    assert str(333) in err, \
        'When pkdi called, arg chould be converted to str,'