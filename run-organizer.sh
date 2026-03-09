#!/bin/bash
# Wrapper script for file-organizer launchd job
# Grant Full Disk Access to THIS script (not Python) for security
cd "/Users/jelmer/Dev/file-organizer"
/usr/bin/python3 organize.py "$@"
