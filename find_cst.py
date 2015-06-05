# Copyright 2013 - 2015 Mirantis, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import json
import os
import sys
import subprocess

components = ['nova', 'novaclient', 'cinder', 'cinderclient', 'neutron']

def execute_return_dict(cmd):
    """Run cmd (string) and return its output"""
    print (cmd)
    run = subprocess.Popen(cmd, stdin=None, bufsize=1024 * 1024,
                           stdout=subprocess.PIPE, stderr=None)
    total = dict()
    while True:
        out = run.stdout.readline()
        if out == '' and run.poll() is not None:
            break
        if out:
            total[out.split("  ")[1].strip()] = out.split("  ")[0]
#   print (total)
    return total or None


def gather_data(path):
    """Traverse path and gather md5 form py-files"""

    data = dict()

    for component in components:
        workdir = path + "/" + component + "/"
        cmd = ["/usr/bin/find", workdir,'-name', '*.py', '-exec', '/usr/bin/md5sum','{}',';']

        run = subprocess.Popen(cmd, stdin=None, bufsize=1024 * 1024,
                               stdout=subprocess.PIPE, stderr=None)
        store = dict()
        while True:
            out = run.stdout.readline()
            if out == '' and run.poll() is not None:
                break
            if out:
                tmp = out.split("  ")
                store[tmp[1].strip().replace(workdir, '')] = tmp[0] 

        data[component] = store

    return data


def main():
    data = gather_data('/usr/lib/python2.7/dist-packages')
    with open("files-md5.json", "w") as fp:
        json.dump(data,fp)



if __name__ == '__main__':
    main()
