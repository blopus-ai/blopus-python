"""Single source of truth for the package version.

Bump this on every release (see PUBLISH.md). It also feeds the User-Agent
header, so a correct value here is what keeps Cloudflare from 1010-blocking
requests as an unidentified library.
"""

__version__ = "0.3.5"
