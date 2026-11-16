#!/bin/zsh
# Refresh Mieux's local data: Open Food Facts (monthly CSV export) and Open Prices (daily export). The app keeps running; each file is swapped atomically.
#   ./update_data.sh ~/Downloads/en.openfoodfacts.org.products.csv     # after downloading the new export from https://world.openfoodfacts.org/data
#   ./update_data.sh                                                    # prices only
cd "$(dirname "$0")/backend" || exit 1
[ -n "$1" ] && .venv/bin/python -m scripts.import_off_dump "$1"
.venv/bin/python -m scripts.import_prices_dump
