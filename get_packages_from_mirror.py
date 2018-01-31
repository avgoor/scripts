import gzip
import io
import os
import re
import urllib2
import xml.etree.ElementTree as ET

from contextlib import closing

def get_ubuntu_packages():
    mirror_url = "http://mirror.fuel-infra.org/mos-repos/ubuntu/snapshots" \
                 "/9.0-latest/dists/mos9.0-proposed/main/binary-amd64/Packages"

    with closing(urllib2.urlopen(mirror_url)) as data:
        expr = re.compile("^Package:\s(.*).*\n.*\nVersion: (.*)$", re.M)
        matched = re.findall(expr, data.read())
    return matched


def get_centos_packages():

    baseurl = "http://mirror.fuel-infra.org/mos-repos/centos/" \
              "mos9.0-centos7/snapshots/proposed-latest/x86_64/repodata/"
    
    with closing(urllib2.urlopen(baseurl)) as listing:
        primary_xml_gz_file = re.findall(
            "^.*\"(\S+.primary.xml.gz).*$", listing.read(), re.M)[0]

    with closing(urllib2.urlopen(
        "{}/{}".format(baseurl, primary_xml_gz_file))) as fd:
        primary_xml_gz = fd.read()

    with io.BytesIO(primary_xml_gz) as primary_xml_gz_fd:
        zp = gzip.GzipFile(mode='rb', fileobj=primary_xml_gz_fd)
        data = ET.parse(zp).getroot()

    ret = []
    for child in data.iter('{http://linux.duke.edu/metadata/common}package'):
        name = child.find('{http://linux.duke.edu/metadata/common}name').text
        version = child.find('{http://linux.duke.edu/metadata/common}version')
        ver = version.get('ver')
        rel = version.get('rel')
        ret.append(("{}".format(name), "{}-{}".format(ver, rel)))
    return ret

def print_packages(pkgs_list):
    for pkg, ver in pkgs_list:
        print "   {}, {}".format(pkg, ver)

if __name__ == "__main__":
    print """
.. csv-table:: Ubuntu packages
   :header: "Package name", "Package version"
   :widths: 15, 20
"""
    print_packages(get_ubuntu_packages())
    print """
.. csv-table:: CentOS packages
   :header: "Package name", "Package version"
   :widths: 15, 20
"""
    print_packages(get_centos_packages())
