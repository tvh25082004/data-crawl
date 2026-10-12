#!/bin/zsh
cd "$(dirname "$0")"
python3 run.py params 2>&1
python3 run.py images 2>&1
python3 run.py normalize excel 2>&1
echo "PIPELINE_COMPLETE"
