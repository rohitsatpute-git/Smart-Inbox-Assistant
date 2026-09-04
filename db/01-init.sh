#!/bin/bash
set -euo pipefail
echo "Initializing SMARTINBOX schema as APP_USER..."
sqlplus -s "${APP_USER}/${APP_USER_PASSWORD}@//localhost/FREEPDB1" @"/opt/smart-inbox/schema.sql"
echo "Schema init complete."
