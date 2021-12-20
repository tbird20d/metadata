#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
#
# This script is a python version of metadata.pl, from TuxMake.
#
# Usage: metadata.py <spec.ini >metadata.json
#
# This script for extracts metadata from the build runtime environment in a
# single shot. It should receive a file containing a metadata extraction
# specification in INI format as its first argument. The format is the
# following:
#
# {
#   "section1": {
#     "key1": "command1 ...",
#     "key2": "command2 ...",
#     [...]
#     "keyN": "commandN ..."
#   },
#   "section2": {
#     "key1": "command1 ...",
#     "key2": "command2 ...",
#     [...]
#     "keyN": "commandN ..."
#   },
#   [...]

import sys
import os
import subprocess
import configparser
import json
import tempfile

# read spec
spec = configparser.ConfigParser()
spec.read_string(sys.stdin.read())

metadata = {}
for section in spec.sections():
    if section in ["meta", "types"]:
        continue
    metadata[section] = {}
    for key in spec[section]:
        cmd = spec[section][key].rstrip()

        # do variable substitution in the cmd
        if "{compiler}" in cmd:
            if "CC" in os.environ:
                compiler = os.environ["CC"]
            else:
                compiler = "cc"

            if "CROSS_COMPILER" in os.environ:
                prefix = os.environ["CROSS_COMPILER"]
                compiler = prefix + compiler
            cmd = cmd.replace("{compiler}", compiler)

        if "{src_dir}" in cmd:
            if "SRC_DIR" in os.environ:
                src_dir = os.environ["SRC_DIR"]
            else:
                src_dir = os.getcwd()

            cmd = cmd.replace("{src_dir}", src_dir)

        # remove "head -n 1" and set a flag to replace it's functionality
        if cmd.endswith("| head -n 1"):
            use_first_line = True
            cmd = cmd[:-11].rstrip()
        else:
            use_first_line = False

        metadata[section][key] = cmd
        fd, script_name = tempfile.mkstemp()
        os.write(fd, cmd.encode('utf-8'))
        os.close(fd)
        completed_proc = subprocess.run(["/bin/sh", script_name],
                capture_output=True)
        os.remove(script_name)
        result = completed_proc.stdout.strip()
        if use_first_line:
            result = result.split(b"\n")[0]
        if completed_proc.returncode != 0:
            sys.stderr.write("Warning: Error running cmd '%s'\n" % cmd)
            metadata[section][key] = "Error running '%s'" % cmd
        else:
            if result:
                metadata[section][key] = result.decode('utf-8')
            else:
                sys.stderr.write("Warning: no output for '%s' cmd '%s'\n" % (key, cmd))
                metadata[section][key] = "No output for '%s'" % cmd

print(json.dumps(metadata, sort_keys=True, indent=4))
