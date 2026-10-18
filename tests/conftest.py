"""
Installs the fake Live API, then loads the repo as the `fcb1010` package
so the tests can import it like Live does.
"""
import importlib.util
import pathlib
import sys

import pytest

from fakes import ableton, live

sys.modules["Live"] = live.build_module()
sys.modules.update(ableton.build_modules())

ROOT = pathlib.Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location(
	"fcb1010", ROOT / "__init__.py", submodule_search_locations=[str(ROOT)])
_package = importlib.util.module_from_spec(_spec)
sys.modules["fcb1010"] = _package
_spec.loader.exec_module(_package)

from harness import Rig  # noqa: E402


@pytest.fixture
def song():
	return live.reset()


@pytest.fixture
def rig(song, monkeypatch):
	r = Rig(song)
	monkeypatch.setattr("fcb1010.transport.time", lambda: r.clock)
	yield r
	if r.surface is not None:
		r.disconnect()
	assert live.errors == [], "Exceptions were raised inside Live callbacks: {!r}".format(live.errors)
