#!/bin/sh
# l.sh lo hi : lst.py listing without the elision notes
here=$(cd "$(dirname "$0")" && pwd)
. "$here/env.sh"
exec "$py" "$here/lst.py" "$1" "$2" | grep -v '^  ; \.\.\.'
