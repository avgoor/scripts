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

# This is the list of components which will be check or gather md5 from.
# Here should be all OpenStack components including clients
components = ['nova', 'novaclient', 'cinder', 'cinderclient', 'neutron']


def gather_data(path):
    """Traverse path and gather md5 from py-files"""

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

    filename = "files.md5"
    print sys.argv
    for cmd in sys.argv[1:]:
        if '--file' in cmd:
            filename = cmd.split("=")[1]
        if '--gather' in cmd:
            gather = True
        if '--release' in cmd:
            release = cmd.split("=")[1]
 
    if not release:
        print ("NEED TO SET RELEASE!")
        sys.exit(1)
 
    data = dict()
    with open(filename, "r") as fp:
        data = json.load(fp)

    data[release] = gather_data('/usr/lib/python2.7/dist-packages')
    data['paths'] = {"ubuntu": "/usr/lib/python2.7/dist-packages",
                     "centos": "/usr/lib/python2.6/site-packages"}
    with open(filename, "w") as fp:
        json.dump(data,fp)



if __name__ == '__main__':
    main()
