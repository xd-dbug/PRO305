"""Make the shared Lambda layer importable as `shared.*` during tests.

In deployed Lambdas this works because SAM mounts the layer content
(backend/layer/) onto the function's import path. Locally, pytest needs a
little help finding it since backend/auth, backend/recipes, etc. import
`shared.*` directly (e.g. `from shared.auth_middleware import require_auth`).
"""

import sys
from pathlib import Path

LAYER_ROOT = Path(__file__).parent / "layer"
if str(LAYER_ROOT) not in sys.path:
    sys.path.insert(0, str(LAYER_ROOT))
