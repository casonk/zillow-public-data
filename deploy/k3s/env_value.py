"""Print KEY=value for one key of a systemd-style env file, without the quotes systemd would strip.

systemd's EnvironmentFile accepts KEY="value with spaces"; `kubectl create secret --from-env-file` keeps the
quotes literally, which made a pod reject a quoted setting. This reads the file the way systemd does.
Prints nothing when the key is absent. Usage: env_value.py FILE KEY
"""

from __future__ import annotations

import re
import sys


def value_of(text: str, key: str) -> str | None:
    found = None
    for line in text.splitlines():
        match = re.match(rf"\s*{re.escape(key)}\s*=\s*(.*?)\s*$", line)
        if match:
            value = match.group(1)
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]
            found = value  # the last assignment wins, as in systemd
    return found


def main(argv: list[str]) -> int:
    path, key = argv
    with open(path, encoding="utf-8") as stream:
        value = value_of(stream.read(), key)
    if value is not None:
        print(f"{key}={value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
