"""A shell-level FORCE_COLOR (set by some terminal wrappers) makes Rich emit ANSI
codes even into a captured, non-tty stream, breaking plain-text CLI assertions.
`ladder.cli` builds its Console singleton at import time, so this must run before
that import happens anywhere in the test session.
"""

import os

os.environ.pop("FORCE_COLOR", None)
os.environ["NO_COLOR"] = "1"
