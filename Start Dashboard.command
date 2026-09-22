#!/bin/zsh
set -e
repo_dir=${0:A:h}
cd "$repo_dir"
port=$(/usr/bin/python3 -c 'import json; print(json.load(open("config.json")).get("dashboard_port",48763))')
if ! /usr/bin/nc -z 127.0.0.1 "$port" 2>/dev/null; then
  nohup .venv/bin/python dashboard_service/server.py > service.log 2> service-error.log < /dev/null &
fi
open "$repo_dir/dashboard/index.html"
