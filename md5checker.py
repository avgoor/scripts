import json
import os
import subprocess
import sys

components = [
    "nova",
    "novaclient",
    "neutron",
    "neutronclient",
    "cinder",
    "cinderclient",
    "glance",
    "glanceclient",
    "keystone",
    "keystoneclient"
]

def usage(err=None):
    if err:
        print ("Error: " + err)
    print("""
MOS release consistency checker.
Opts
====
    --release      Set Fuel release
    --filename     Set name of file to use as database

Usage
=====
    Checking consistency of MOS assuming that it is Fuel 6.0 release
    python md5checker.py --release=6.0 --os=ubuntu --check

    Gathering data for database assumuning that the release is 6.0-mu4
    python md5checker.py --release=6.0-mu4 --os=centos --gather
    """)
    sys.exit(1)

def opts_parse():
    # setting up defaults
    cfg = {
        "version": "0.1",
        "release": None,
        "os": "ubuntu",
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

    return cfg


class Gatherer(object):
    def __init__(self, cfg):
        self.cfg = dict(cfg)
        try:
            with open(self.cfg['filename'], 'r') as fp:
                self.cfg['data'] = json.load(fp)
        except:
            self.cfg['data'] = self.__prepare_structure()

    def __prepare_structure(self):
        data = dict()
        data[self.cfg['release']] = dict()
        return data

    def __gather(self):
        for component in components:
            fdir = self.cfg['path'][self.cfg['os']] + "/" + \
                component + "/"
            cmd = ["/usr/bin/find", fdir, '-name', '*.py',
                   '-exec', '/usr/bin/md5sum','{}',';']
            run = subprocess.Popen(
                cmd,
                bufsize=1024 * 1024 * 8,
                stdin=None,
                stdout=subprocess.PIPE,
                stderr=None
            )
            while not stop:
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

    def __store_gathered(self):
        if self.cfg['data']:
            with open(self.cfg['filename'], 'w') as fp:
                json.dump(self.cfg['data'], fp)

    def do(self):
        self.__gather()
        self.__store_gathered()


class Checker(object):
    def __init__(self, cfg):
        self.cfg = dict(cfg)

    def do(self):
        pass
def main():
    cfg = opts_parse()
    if cfg['action'] == 'gather':
        Actor = Gatherer(cfg)
    else:
        Actor = Checker(cfg)

    Actor.do()

if __name__ == "__main__":
    main()
