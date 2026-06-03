"""Pytest configuration — ensures `features.*` and `streamlit_app.*` import
cleanly when the test runner is invoked from anywhere in the repo.
"""

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
