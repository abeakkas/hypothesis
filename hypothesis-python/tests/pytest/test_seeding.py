# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2018 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# CONTRIBUTING.rst for a full list of people who may hold copyright, and
# consult the git log if you need to determine who owns an individual
# contribution.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.
#
# END HEADER

from __future__ import division, print_function, absolute_import

import re

import pytest

from hypothesis.internal.compat import hrange

pytest_plugins = str('pytester')


TEST_SUITE = """
from hypothesis import given, settings, assume
import hypothesis.strategies as st


first = None

@settings(database=None)
@given(st.integers())
def test_fails_once(some_int):
    assume(abs(some_int) > 10000)
    global first
    if first is None:
        first = some_int

    assert some_int != first
"""


CONTAINS_SEED_INSTRUCTION = re.compile(r"--hypothesis-seed=\d+", re.MULTILINE)


@pytest.mark.parametrize('seed', [0, 42, 'foo'])
def test_runs_repeatably_when_seed_is_set(seed, testdir):
    script = testdir.makepyfile(TEST_SUITE)

    results = [
        testdir.runpytest(
            script, '--verbose', '--strict', '--hypothesis-seed', str(seed)
        )
        for _ in hrange(2)
    ]

    for r in results:
        for l in r.stdout.lines:
            assert '--hypothesis-seed' not in l

    failure_lines = [
        l
        for r in results
        for l in r.stdout.lines
        if 'some_int=' in l
    ]

    assert len(failure_lines) == 2
    assert failure_lines[0] == failure_lines[1]


HEALTH_CHECK_FAILURE = """
import os

from hypothesis import given, strategies as st, assume, reject

RECORD_EXAMPLES = <file>

if os.path.exists(RECORD_EXAMPLES):
    target = None
    with open(RECORD_EXAMPLES, 'r') as i:
        seen = set(map(int, i.read().strip().split("\\n")))
else:
    target = open(RECORD_EXAMPLES, 'w')

@given(st.integers())
def test_failure(i):
    if target is None:
        assume(i not in seen)
    else:
        target.write("%s\\n" % (i,))
        reject()
"""


def test_repeats_healthcheck_when_following_seed_instruction(testdir, tmpdir):
    health_check_test = HEALTH_CHECK_FAILURE.replace(
        '<file>', repr(str(tmpdir.join('seen'))))

    script = testdir.makepyfile(health_check_test)

    initial = testdir.runpytest(script, '--verbose', '--strict',)

    match = CONTAINS_SEED_INSTRUCTION.search('\n'.join(initial.stdout.lines))
    initial_output = '\n'.join(initial.stdout.lines)

    match = CONTAINS_SEED_INSTRUCTION.search(initial_output)
    assert match is not None

    rerun = testdir.runpytest(script, '--verbose', '--strict', match.group(0))
    rerun_output = '\n'.join(rerun.stdout.lines)

    assert 'FailedHealthCheck' in rerun_output
    assert '--hypothesis-seed' not in rerun_output

    rerun2 = testdir.runpytest(
        script, '--verbose', '--strict', '--hypothesis-seed=10')
    rerun2_output = '\n'.join(rerun2.stdout.lines)
    assert 'FailedHealthCheck' not in rerun2_output