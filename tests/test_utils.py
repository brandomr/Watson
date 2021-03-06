# -*- coding: utf-8 -*-
"""Unit tests for the 'utils' module."""

import functools
import os
import datetime

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO

import pytest
from dateutil.tz import tzutc

from watson.utils import (get_start_time_for_period, make_json_writer,
                          safe_save, parse_tags, PY2)
from . import mock_datetime


_dt = functools.partial(datetime.datetime, tzinfo=tzutc())


@pytest.mark.parametrize('now, mode, start_time', [
    (_dt(2016, 6, 2), 'year', _dt(2016, 1, 1)),
    (_dt(2016, 6, 2), 'month', _dt(2016, 6, 1)),
    (_dt(2016, 6, 2), 'week', _dt(2016, 5, 30)),
    (_dt(2016, 6, 2), 'day', _dt(2016, 6, 2)),
    (_dt(2016, 6, 2), 'all', _dt(1970, 1, 1)),
    (_dt(2016, 6, 2), 'luna', _dt(2016, 5, 21, 21, 16)),

    (_dt(2012, 2, 24), 'year', _dt(2012, 1, 1)),
    (_dt(2012, 2, 24), 'month', _dt(2012, 2, 1)),
    (_dt(2012, 2, 24), 'week', _dt(2012, 2, 20)),
    (_dt(2012, 2, 24), 'day', _dt(2012, 2, 24)),
    (_dt(2012, 2, 24), 'all', _dt(1970, 1, 1)),
    (_dt(2012, 2, 24), 'luna', _dt(2012, 2, 7, 21, 56)),
])
def test_get_start_time_for_period(now, mode, start_time):
    with mock_datetime(now, datetime):
        assert get_start_time_for_period(mode).datetime == start_time


def test_make_json_writer():
    fp = StringIO()
    writer = make_json_writer(lambda: {'foo': 42})
    writer(fp)
    assert fp.getvalue() == '{\n "foo": 42\n}'


def test_make_json_writer_with_args():
    fp = StringIO()
    writer = make_json_writer(lambda x: {'foo': x}, 23)
    writer(fp)
    assert fp.getvalue() == '{\n "foo": 23\n}'


def test_make_json_writer_with_kwargs():
    fp = StringIO()
    writer = make_json_writer(lambda foo=None: {'foo': foo}, foo='bar')
    writer(fp)
    assert fp.getvalue() == '{\n "foo": "bar"\n}'


def test_make_json_writer_with_unicode():
    fp = StringIO()
    writer = make_json_writer(lambda: {u'ùñï©ôð€': u'εvεrywhεrε'})
    writer(fp)
    expected = u'{\n "ùñï©ôð€": "εvεrywhεrε"\n}'
    if PY2:
        expected = expected.encode('utf-8')
    assert fp.getvalue() == expected


def test_safe_save(config_dir):
    save_file = os.path.join(config_dir, 'test')
    backup_file = os.path.join(config_dir, 'test' + '.bak')

    assert not os.path.exists(save_file)
    safe_save(save_file, lambda f: f.write("Success"))
    assert os.path.exists(save_file)
    assert not os.path.exists(backup_file)

    with open(save_file) as fp:
        assert fp.read() == "Success"

    safe_save(save_file, "Again")
    assert os.path.exists(backup_file)

    with open(save_file) as fp:
        assert fp.read() == "Again"

    with open(backup_file) as fp:
        assert fp.read() == "Success"

    assert os.path.getmtime(save_file) >= os.path.getmtime(backup_file)


def test_safe_save_tmpfile_on_other_filesystem(config_dir, mock):
    save_file = os.path.join(config_dir, 'test')
    backup_file = os.path.join(config_dir, 'test' + '.bak')

    assert not os.path.exists(save_file)
    safe_save(save_file, lambda f: f.write("Success"))
    assert os.path.exists(save_file)
    assert not os.path.exists(backup_file)

    with open(save_file) as fp:
        assert fp.read() == "Success"

    # simulate tmpfile being on another file-system
    # OSError is caught and handled by shutil.move() used by save_safe()
    mock.patch('os.rename', side_effect=OSError)
    safe_save(save_file, "Again")
    assert os.path.exists(backup_file)

    with open(save_file) as fp:
        assert fp.read() == "Again"


def test_safe_save_with_exception(config_dir):
    save_file = os.path.join(config_dir, 'test')
    backup_file = os.path.join(config_dir, 'test' + '.bak')

    def failing_writer(f):
        raise RuntimeError("Save failed.")

    assert not os.path.exists(save_file)

    with pytest.raises(RuntimeError):
        safe_save(save_file, failing_writer)

    assert not os.path.exists(save_file)
    assert not os.path.exists(backup_file)

    safe_save(save_file, lambda f: f.write("Success"))
    assert os.path.exists(save_file)
    assert not os.path.exists(backup_file)

    with pytest.raises(RuntimeError):
        safe_save(save_file, failing_writer)

    with open(save_file) as fp:
        assert fp.read() == "Success"

    assert not os.path.exists(backup_file)


@pytest.mark.parametrize('args, parsed_tags', [
    (['+ham', '+n', '+eggs'], ['ham', 'n', 'eggs']),
    (['+ham', 'n', '+eggs'], ['ham n', 'eggs']),
    (['ham', 'n', '+eggs'], ['eggs']),
    (['ham', '+n', 'eggs'], ['n eggs']),
    (['+ham', 'n', 'eggs'], ['ham n eggs']),
])
def test_parse_tags(args, parsed_tags):
    tags = parse_tags(args)
    assert tags == parsed_tags
