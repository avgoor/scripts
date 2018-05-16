#!/usr/bin/env python

import re
import urllib2

from contextlib import closing

REPOS = [
    'http://mirror.fuel-infra.org/mos-repos/ubuntu/7.0/dists/mos7.0/main/binary-amd64/Packages',
    'http://mirror.fuel-infra.org/mos-repos/ubuntu/7.0/dists/mos7.0-updates/main/binary-amd64/Packages'
]

def merge_dicts(dict1, dict2):
    tmp = dict1.copy()
    tmp.update(dict2)
    return tmp

def get_packages_from_url_debian(url):
    with closing(urllib2.urlopen(url)) as data:
        expr = re.compile(r"^Package:\s(.*)\n(?:.*\n)?Version:\s(.*)$", re.M)
        matched = re.findall(expr, data.read())
    
    return {k:v for k,v in matched}

if __name__ == "__main__":
    packages = {}
    for repo in REPOS:

        packages = merge_dicts(
            packages, 
            get_packages_from_url_debian(repo)
        )

    for k in sorted(packages.keys()):
        print "{},{}".format(k,packages[k])