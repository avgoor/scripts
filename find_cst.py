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


import os
import sys
import subprocess

components = ['nova', 'novaclient', 'cinder', 'cinderclient', 'neutron']

def get_md5_from_file(file):
    """ Gets md5 checksum from file by calling external tool."""
    run = subprocess.Popen(["md5sum", file], stdin=None,
                           stdout=subprocess.PIPE, stderr=None)
    run.wait()

    if run.returncode == 0:
        md5 = run.communicate()[0].split('  ')[0]
    else:
        md5 = None

    return md5


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
    data = dict()
    for component in components:
        workdir = path + "/" + component + "/"
        cmd = ["/usr/bin/find", workdir,'-name', '*.py', '-exec', '/usr/bin/md5sum','{}',';']
        data['component'] = execute_return_dict(cmd)
    print (data)
    pass


def main():
    gather_data('/usr/lib/python2.7/dist-packages')
    pass


if __name__ == '__main__':
    main()
