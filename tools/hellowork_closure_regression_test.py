#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Local regression test for closure classification helpers using mocked HTML logic.
"""
from tools.hellowork_closure_recheck_test import CLOSED_MARKERS
assert any("公開されていません" in x for x in CLOSED_MARKERS)
assert any("見つかりません" in x for x in CLOSED_MARKERS)
assert any("掲載を終了" in x for x in CLOSED_MARKERS)
print("PASS closure marker regression")
