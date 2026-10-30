"""Write the FastAPI OpenAPI schema to a file, for the web client's generated types."""

import json
import sys
from pathlib import Path

from behique.main import create_app

Path(sys.argv[1]).write_text(json.dumps(create_app(rescan=False).openapi(), indent=2) + "\n")
