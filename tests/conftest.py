# Pytest configuration for GPS-Tracking-Server tests.
# asyncio_mode is set in pytest.ini.

import sys
from pathlib import Path

# Add project root so 'from api. ...' works when pytest runs from repo root (e.g. in CI).
_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))
