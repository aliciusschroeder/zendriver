#!/bin/sh
echo "[ERROR] bind() failed: Address already in use; Cannot start http server for devtools." >&2
exit 1
