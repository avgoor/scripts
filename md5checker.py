#!/usr/bin/env python
# Copyright 2015 Mirantis, Inc.
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
import subprocess
import sys
import urllib2

components = [
    "nova",
    "novaclient",
    "neutron",
    "neutronclient",
    "cinder",
    "cinderclient",
    "glance",
    "glanceclient",
    "glance_store",
    "swift",
    "swift3",
    "swiftclient",
    "heat",
    "heatclient",
    "horizon",
    "oslo",
    "murano",
    "muranoclient",
    "muranodashboard",
    "sahara",
    "ceilometerclient",
    "ceilometer",
    "saharaclient",
    "keystone",
    "keystonemiddleware",
    "keystoneclient"
]

def usage(err=None):
    if err:
        print ("Error: " + err)
    print("""
MOS release consistency checker.
Options
====
    --release      Set Fuel release
    --filename     Set name of file to use as a database
    --os           Set os version (centos/ubuntu)

Usage
=====
    Checking consistency of MOS assuming that it is Fuel 6.0 release
    python md5checker.py --release=6.0 --os=ubuntu --check

    Gathering data for database assuming that the release is 6.0-mu4
    python md5checker.py --release=6.0-mu4 --os=centos --gather
    """)
    sys.exit(1)

def opts_parse():
    # setting up defaults
    cfg = {
        "version": "0.1",
        "release": None,
        "os": "ubuntu",
        "username" : "admin",
        "password": "admin",
        "tenant": "admin",
        "path": {
            "ubuntu": "/usr/lib/python2.7/dist-packages",
            "centos": "/usr/lib/python2.6/site-packages"
        },
        "filename": "md5checker.dat",
        "action": "check"
    }
    if len(sys.argv) < 2:
        usage("At least --release must be set!")
    for opt in sys.argv:
        if '--gather' in opt:
            cfg['action'] = 'gather'
        if '--release' in opt:
            cfg['release'] = opt.split("=")[1]
        if '--os' in opt:
            cfg['os'] = opt.split("=")[1]
        if '--filename' in opt:
            cfg['filename'] = opt.split("=")[1]
        if '--user' in opt:
            cfg['username'] = opt.split("=")[1]
        if '--pass' in opt:
            cfg['password'] = opt.split("=")[1]
        if '--tenant' in opt:
            cfg['tenant'] = opt.split("=")[1]

    return cfg



class Gatherer(object):
    def __init__(self, cfg):
        self.cfg = dict(cfg)
        try:
            with open(self.cfg['filename'], 'r') as fp:
                self.cfg['data'] = json.load(fp)
        except:
            self.cfg['data'] = self._prepare_structure()
        if self.cfg['release'] is None:
            usage("--release must be set!")
        if self.cfg['release'] not in self.cfg['data'].keys():
            self.cfg['data'][self.cfg['release']] = dict()

    def _prepare_structure(self):
        data = dict()
        data[self.cfg['release']] = dict()
        return data

    def _gather(self):
        for component in components:
            fdir = self.cfg['path'][self.cfg['os']] + "/" + \
                component + "/"
            cmd = ["/usr/bin/find", fdir, '-name', '*.py',
                   '-exec', '/usr/bin/md5sum','{}',';']
            run = subprocess.Popen(
                cmd,
                stdin=None,
                stdout=subprocess.PIPE,
                stderr=None
            )
            while True:
                out = run.stdout.readline()
                if out == '' and run.poll() is not None:
                    break
                if out:
                    tmp = out.split("  ")
                    md5 = tmp[0]
                    fl = tmp[1].strip().replace(fdir, '')
                    try:
                        self.cfg['data'][self.cfg['release']][component][fl] = md5
                    except KeyError:
                        self.cfg['data'][self.cfg['release']].update({component:{fl:md5}})

    def _store_gathered(self):
        if self.cfg['data']:
            with open(self.cfg['filename'], 'w') as fp:
                json.dump(self.cfg['data'], fp)

    def do(self):
        self._gather()
        self._store_gathered()


class Checker(Gatherer):
    def __init__(self, cfg):
        self.cfg = dict(cfg)
        self.cfg['data'] = self._prepare_structure()
        self.old_cfg = dict(cfg)
        try:
            with open(self.cfg['filename'], 'r') as fp:
                self.old_cfg['data'] = json.load(fp)
        except:
            usage("Datafile not accessible!")
        if self.cfg['release'] not in self.cfg['data'].keys():
            usage("Target release is not in database!")


    def _check(self):
        self.report = dict()
        for component in components:
            try:
                db = self.old_cfg['data'][self.cfg['release']][component]
                got = self.cfg['data'][self.cfg['release']][component]
                missing = set(db.keys()) - set(got.keys())
                self.report[component] = {
                    "total": len(got.keys())
                }
                if len(missing) > 0:
                    self.report[component].update({
                        "missing": len(missing),
                        "missing_names" : missing
                        }
                    )
                corrupt = set()
                for key in got.keys():
                    if got[key] != db[key]:
                        corrupt.add(key)
                if len(corrupt) > 0:
                    self.report[component].update({
                        "corrupt": len(corrupt),
                        "corrupt_names": corrupt
                    })
            except KeyError as e:
                pass

    def _make_report(self):
        print (self.report)
        pass

    def get_nodes_json(self):
        
        psw = self.cfg['password']
        uname = self.cfg['username']
        tenant = self.cfg['tenant']

        req = urllib2.Request('http://172.16.59.34:5000/v2.0/tokens')
        req.add_header('Content-Type', 'application/json')
        req.add_data('
            {"auth":{
                "passwordCredentials":
                {
                    "password":"{psw}",
                    "username":"{uname}"
                },
                "tenantName":"{tenant}"
            }}
        '.format(psw=psw, uname=uname, tenant=tenant))
        token = json.load(urllib2.urlopen(req))['access']['token']['id']
        req = urllib2.Request('http://172.16.59.34:8000/api/v1/nodes')
        req.add_header('X-Auth-Token', token)
        return json.load(urllib2.urlopen(req))

    def do(self):
        self._gather()
        self._check()
        self._make_report()


def main():
    cfg = opts_parse()
    if cfg['action'] == 'gather':
        Actor = Gatherer(cfg)
    else:
        Actor = Checker(cfg)

    Actor.do()

if __name__ == "__main__":
    main()
