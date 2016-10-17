#!/usr/bin/env python
# encoding: utf-8

import sys
import yaml


def get_report():
    """
    Takes filename of astute's report yaml
    :type filename: str
    :rtype: list
    """
    tmp = yaml.load(sys.stdin)
    return [x for x in tmp if _is_noop_report(x)]


def _is_noop_report(report):
    """
    Takes report and checks for needed fields
    :param report: - dict of dicts
    :rtype: bool
    """
    try:
        return 'noop' in report['summary']['events']
    except (KeyError, AttributeError, TypeError):
        return False

if __name__ == "__main__":
    r1 = get_report()
    out = []
    for a in r1:
        out.append("\nTask {}: \n".format(a['task_name']))
        for r in a['summary']['raw_report']:
            out.append(" | {} : {}\n".format(r['source'], r['message']))

    print "".join(out)
