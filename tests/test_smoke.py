import os
import sys


def test_app_exists():
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    from app import app

    assert app is not None
