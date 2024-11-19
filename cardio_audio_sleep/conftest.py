from __future__ import annotations

import os
from tempfile import NamedTemporaryFile
from typing import TYPE_CHECKING

from .utils.logs import logger

if TYPE_CHECKING:
    import pytest


lsl_cfg = NamedTemporaryFile("w", prefix="lsl", suffix=".cfg", delete=False)
if "LSLAPICFG" not in os.environ:
    with lsl_cfg as fid:
        fid.write("[multicast]\nResolveScope = link")
    os.environ["LSLAPICFG"] = lsl_cfg.name


def pytest_configure(config: pytest.Config) -> None:
    """Configure pytest options."""
    warnings_lines = r"""
    error::
    # Matplotlib deprecation issued in VSCode test debugger
    ignore:.*interactive_bk.*:matplotlib._api.deprecation.MatplotlibDeprecationWarning
    """
    for warning_line in warnings_lines.split("\n"):
        warning_line = warning_line.strip()
        if warning_line and not warning_line.startswith("#"):
            config.addinivalue_line("filterwarnings", warning_line)
    # setup logging
    logger.propagate = True


def pytest_sessionfinish(session, exitstatus) -> None:
    """Clean up the pytest session."""
    try:
        os.unlink(lsl_cfg.name)
    except Exception:
        pass
