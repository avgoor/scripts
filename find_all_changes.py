from __future__ import print_function

import json
import urllib2


def get_gerrit_data():
    """
    :rtype: list
    """
    request = "https://review.openstack.org/changes/?q=status:merged+project:"\
              "openstack/fuel-library+branch:stable/mitaka+after:2016-07-01"
    f = urllib2.urlopen(request).read().lstrip(")]}'")  # Anti-XSSI
    data = json.loads(f)
    return data

if __name__ == "__main__":
    insertions = 0
    deletions = 0
    is_bug = 0
    changes = get_gerrit_data()
    print (len(changes))
    for change in changes:
        insertions += change['insertions']
        deletions += change['deletions']
        if 'topic' in change:
            is_bug += 1 if 'bug' in change['topic'] else 0
        print (change['subject'])
    print ("Added: {}, Deleted: {}, Bugs: {}".format(insertions, deletions,
                                                     is_bug))
