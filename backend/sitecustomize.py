"""Windows compatibility shim for the Unix-only `resource` module.

`safeuploads` imports ``resource`` unconditionally (``getrusage`` /
``RUSAGE_SELF``) to enforce memory limits during file validation. On Windows
the module does not exist, so any import of the backend fails. This module
installs a minimal stand-in backed by ``psutil`` (already a project dependency)
when running on Windows, so the backend can import and run natively there.

Loaded automatically by the interpreter's `site` machinery when this file
sits in a ``sys.path`` entry (e.g. ``python -m uvicorn ...`` from the backend
directory), or explicitly from ``tests/conftest.py``.
"""

import sys


def install_resource_shim() -> None:
    """Install the fake ``resource`` module if the real one is unavailable."""
    if sys.platform != "win32" or "resource" in sys.modules:
        return

    try:
        import psutil
    except ImportError:
        return

    import types

    module = types.ModuleType("resource")
    module.RUSAGE_SELF = 0

    def getrusage(who: int = module.RUSAGE_SELF) -> object:
        del who

        class _Usage:
            ru_maxrss: int

        usage = _Usage()
        usage.ru_maxrss = int(psutil.Process().memory_info().rss)
        return usage

    def getrlimit(*_: object) -> tuple[int, int]:
        return (0, 0)

    def setrlimit(*_: object) -> None:
        return None

    module.getrusage = getrusage
    module.getrlimit = getrlimit
    module.setrlimit = setrlimit
    sys.modules["resource"] = module


install_resource_shim()
