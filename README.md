[variables]
PLAYWRIGHT_BROWSERS_PATH = "0"

[phases.install]
cmds = [
  "pip install -r requirements.txt",
  "playwright install chromium",
  "playwright install-deps chromium"
]

[start]
cmd = "python ticket_monitor.py"
