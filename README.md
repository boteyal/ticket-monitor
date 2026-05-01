[phases.install]
cmds = [
  "pip install -r requirements.txt",
  "playwright install-deps chromium"
]

[start]
cmd = "python ticket_monitor.py"
