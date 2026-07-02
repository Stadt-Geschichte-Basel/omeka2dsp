"""Shared test setup: import path and a deterministic environment.

Loaded by pytest before any test module, so the ``data_2_dasch`` import in the
tests sees these values. Override explicitly (not setdefault) so pre-existing
values on CI or a dev machine cannot make PREFIX differ from "SGB:".
The process exits after the test run, so no restore is needed.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

os.environ.update(
    {
        "ONTOLOGY_NAME": "SGB",
        "API_HOST": "https://api.test.com",
        "PROJECT_SHORT_CODE": "TEST",
        "INGEST_HOST": "https://ingest.test.com",
        "DSP_USER": "test@test.com",
        "DSP_PWD": "testpwd",
    }
)
