#!/usr/bin/env python

import os
import sqlite3
import sys

import libvirt
import netaddr

cfg = dict()
cfg["ENV_NAME"] = os.getenv("ENV_NAME")
cfg["ISO_URL"] = os.getenv("ISO_URL")

# networks defenition
cfg["ADMIN_NET"] = os.getenv("ADMIN_NET", "10.88.0.0/16")
cfg["PUBLIC_NET"] = os.getenv("PUBLIC_NET", "172.18.254.0/24")
cfg["PUB_SUBNET_SIZE"] = int(os.getenv("PUB_SUBNET_SIZE", 28))
cfg["ADM_SUBNET_SIZE"] = int(os.getenv("ADM_SUBNET_SIZE", 28))

#DB
cfg["DB_FILE"] = os.getenv("DB_FILE", "build_cluster.db")

#fuel node credentials
cfg["FUEL_SSH_USERNAME"] = os.getenv("FUEL_SSH_USERNAME", "root")
cfg["FUEL_SSH_PASSWORD"] = os.getenv("FUEL_SSH_PASSWORD", "r00tme")
cfg["KEYSTONE_USERNAME"] = os.getenv("KEYSTONE_USERNAME", "admin")
cfg["KEYSTONE_PASSWORD"] = os.getenv("KEYSTONE_PASSWORD", "admin")
cfg["KEYSTONE_TENANT"] = os.getenv("KEYSTONE_TENANT", "admin")

#nodes settings
cfg["ADMIN_RAM"] = int(os.getenv("ADMIN_RAM", 4096))
cfg["ADMIN_CPU"] = int(os.getenv("ADMIN_CPU", 2))
cfg["SLAVE_RAM"] = int(os.getenv("SLAVE_RAM", 3072))
cfg["SLAVE_CPU"] = int(os.getenv("SLAVE_CPU", 1))
cfg["NODES_COUNT"] = int(os.getenv("NODES_COUNT", 5))

""" Type of deployment:
        TBD
"""
cfg["DEPLOY_TYPE"] = int(os.getenv("DEPLOY_TYPE", 1))

db = None


try:
    vconn = libvirt.open()
except:
    print ("\nERRROR: libvirt is inaccessible!")
    sys.exit(10)


def initialize_database():
    """ This functions initializes DB
        either by creating it or just opening
    """
    global db

    db = sqlite3.Connection(cfg["DB_FILE"])
    cursor = db.cursor()
    try:
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS nets ("
            "net TEXT, "
            "env TEXT, "
            "interface TEXT);"
        )
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS envs ("
            "env TEXT, "
            "owner TEXT, "
            "nodes_count INT, "
            "admin_ram INT, "
            "admin_cpu INT, "
            "slave_ram INT, "
            "slave_cpu INT, "
            "deploy_type INT);"
        )
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS disks ("
            "env TEXT, "
            "node TEXT, "
            "filename TEXT);"
        )
    except:
        print ("Unable to open/create database {0}".format(cfg["DB_FILE"]))
        sys.exit(5)


def pprint_dict(subj):
    if not isinstance(subj, dict):
        return False
    for k, v in sorted(subj.items()):
        print (" {0:20}: {1}".format(k, v))


def env_is_available():
    cursor = db.cursor()
    cursor.execute(
        "SELECT * FROM nets WHERE env='{0}';".format(cfg["ENV_NAME"])
    )
    if cursor.fetchone() is None:
        return True
    return False


def get_free_subnet():
    global cfg
    global db

    sql_query = "SELECT net FROM nets;"
    cursor = db.cursor()
    cursor.execute(sql_query)
    occupied_nets = set(
        netaddr.IPNetwork(x[0]) for x in cursor.fetchall()
    )
    admin_subnets = set(
        x for x in netaddr.IPNetwork(cfg["ADMIN_NET"])
                          .subnet(cfg["ADM_SUBNET_SIZE"])
        if x not in occupied_nets
    )
    public_subnets = set(
        x for x in netaddr.IPNetwork(cfg["PUBLIC_NET"])
                          .subnet(cfg["PUB_SUBNET_SIZE"])
        if x not in occupied_nets
    )

    if not admin_subnets or not public_subnets:
        print ("\nERROR: No more NETWORKS to associate!")
        return False

    cfg["ADMIN_SUBNET"] = sorted(admin_subnets)[0]
    cfg["PUBLIC_SUBNET"] = sorted(public_subnets)[0]
    print (
        "Following subnets will be used:\n"
        " ADMIN_SUBNET:   {0}\n"
        " PUBLIC_SUBNET:  {1}\n".format(cfg["ADMIN_SUBNET"],
                                        cfg["PUBLIC_SUBNET"])
    )
    sql_query = [
        (str(cfg["ADMIN_SUBNET"]), str(cfg["ENV_NAME"]),
         str(cfg["ENV_NAME"] + "_adm")),
        (str(cfg["PUBLIC_SUBNET"]), str(cfg["ENV_NAME"]),
         str(cfg["ENV_NAME"] + "_pub"))
    ]
    print sql_query
    cursor.executemany("INSERT INTO nets VALUES (?,?,?)", sql_query)
    db.commit()
    return True


def register_env():
    cursor = db.cursor()
    cursor.execute(
        "INSERT INTO envs VALUES ('{0}','{1}',{2},{3},{4},{5},{6},{7});"
        .format(cfg["ENV_NAME"], "nobody", cfg["NODES_COUNT"],
                cfg["ADMIN_RAM"], cfg["ADMIN_CPU"], cfg["SLAVE_RAM"],
                cfg["SLAVE_CPU"], cfg["DEPLOY_TYPE"])
    )
    db.commit()


def define_nets():
    network_xml_template = \
        "<network>\n" \
        " <name>{net_name}</name>\n" \
        " <forward mode='route'/>\n" \
        " <ip address='{ip_addr}' prefix='{subnet}'>\n" \
        " </ip>\n" \
        "</network>\n"
    net_name = cfg["ENV_NAME"]+"_adm"
    ip_addr = str(cfg["ADMIN_SUBNET"].ip + 1)
    subnet = cfg["ADMIN_SUBNET"].prefixlen

    net_xml = network_xml_template.format(net_name=net_name,
                                          ip_addr=ip_addr,
                                          subnet=subnet)

    print ("Prepared admin_net xml:\n\n{0}".format(net_xml))

    try:
        vconn.networkCreateXML(net_xml)
    except:
        print ("\nERROR: Unable to create admin subnet in libvirt!")
        sys.exit(11)

    net_name = cfg["ENV_NAME"]+"_pub"
    ip_addr = str(cfg["PUBLIC_SUBNET"].ip + 1)
    subnet = cfg["PUBLIC_SUBNET"].prefixlen

    net_xml = network_xml_template.format(net_name=net_name,
                                          ip_addr=ip_addr,
                                          subnet=subnet)

    print ("Prepared public_net xml:\n\n{0}".format(net_xml))

    try:
        vconn.networkCreateXML(net_xml)
    except:
        print ("\nERROR: Unable to create public subnet in libvirt!")
        sys.exit(11)

    print ("Networks have been successfuly created.")


def define_nodes():
    pass


def start_admin_node():
    pass


def send_keys():
    pass


def wait_for_api_is_ready():
    pass


def start_slaves():
    pass


def configure_nailgun():
    pass


def wait_for_cluster_is_ready():
    pass


def main():
    if '--destroy' in sys.argv:
        print("Destroying {0}".format(cfg["ENV_NAME"]))
        sys.exit(0)
    print("Starting script with following options:\n")
    pprint_dict(cfg)
    if cfg["ENV_NAME"] is None:
        print ("\nERROR: $ENV_NAME must be set!")
        sys.exit(1)
    if cfg["ISO_URL"] is None:
        print ("\nERROR: $ISO_URL must be set!")
        sys.exit(2)
    initialize_database()
    print("\nDatabase ready.\n")
    if not env_is_available():
        print ("\nERROR: $ENV_NAME must be unique! {0} already exists"
               .format(cfg["ENV_NAME"]))
        sys.exit(4)
    if not get_free_subnet():
        sys.exit(3)

    register_env()

    define_nets()

    define_nodes()

    start_admin_node()

    send_keys()

    wait_for_api_is_ready()

    start_slaves()

    configure_nailgun()

    wait_for_cluster_is_ready()

    db.close()

if __name__ == "__main__":
    main()
