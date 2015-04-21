#!/usr/bin/env python

import os
import sqlite3
import sys

import libvirt
import netaddr

cfg = dict()
# required vars
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
cfg["NODES_DISK_SIZE"] = int(os.getenv("NODES_DISK_SIZE", 50))

cfg["STORAGE_POOL"] = os.getenv("STORAGE_POOL", "default")

""" Type of deployment:
        TBD
"""
cfg["DEPLOY_TYPE"] = int(os.getenv("DEPLOY_TYPE", 1))

db = None


try:
    vconn = libvirt.open("qemu:///system")
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


def volume_create(name):
    vol_template = \
        "<volume type='file'>\n" \
        " <name>{vol_name}.img</name>\n" \
        " <allocation>0</allocation>\n" \
        " <capacity unit='G'>{vol_size}</capacity>\n" \
        " <target>\n" \
        "  <format type='qcow2'/>\n" \
        " </target>\n" \
        "</volume>\n"
    try:
        pool = vconn.storagePoolLookupByName(cfg["STORAGE_POOL"])
    except:
        print("\nERROR: libvirt`s storage pool '{0}' is not accessible!"
              .format(cfg["STORAGE_POOL"]))
        sys.exit(12)

    volume = vol_template.format(vol_name=name, vol_size=cfg["NODES_DISK_SIZE"])

    try:
        vol_object = pool.createXML(volume)
    except:
        print("\nERROR: unable to create volume '{0}'!"
              .format(name))
        sys.exit(13)
    print("Created volume from XML:\n\n{0}".format(volume))
    return vol_object


def define_nodes():
    pass


def start_node(name, admin=False):
    vol_obj = volume_create(name)

    node_template_xml = """
<domain type='kvm'>
  <name>{name}</name>
  <memory unit='KiB'>{memory}</memory>
  <currentMemory unit='KiB'>{memory}</currentMemory>
  <vcpu placement='static'>{vcpu}</vcpu>
  <os>
    <type arch='x86_64' machine='pc-i440fx-trusty'>hvm</type>
    <boot dev='{first_boot}'/>
    <boot dev='{second_boot}'/>
    <bios rebootTimeout='5000'/>
  </os>
  <cpu mode='host-model'>
    <model fallback='forbid'/>
  </cpu>
  <clock offset='utc'>
    <timer name='rtc' tickpolicy='catchup' track='wall'>
      <catchup threshold='123' slew='120' limit='10000'/>
    </timer>
    <timer name='pit' tickpolicy='delay'/>
    <timer name='hpet' present='no'/>
  </clock>
  <on_poweroff>destroy</on_poweroff>
  <on_reboot>restart</on_reboot>
  <on_crash>destroy</on_crash>
  <devices>
    <disk type='file' device='disk'>
      <driver name='qemu' type='qcow2' cache='unsafe'/>
      <source file='{hd_volume}'/>
      <target dev='sda' bus='virtio'/>
    </disk>
{iso}
    <controller type='usb' index='0' model='nec-xhci'>
      <alias name='usb0'/>
      <address type='pci' domain='0x0000' bus='0x00' slot='0x08' function='0x0'/>
    </controller>
    <controller type='pci' index='0' model='pci-root'>
      <alias name='pci.0'/>
    </controller>
    <controller type='ide' index='0'>
      <alias name='ide0'/>
      <address type='pci' domain='0x0000' bus='0x00' slot='0x01' function='0x1'/>
    </controller>
    <interface type='network'>
      <source network='{admin_net}'/>
      <target dev='dev'/>
      <model type='virtio'/>
      <alias name='net0'/>
      <address type='pci' domain='0x0000' bus='0x00' slot='0x03' function='0x0'/>
    </interface>
    <interface type='network'>
      <source network='{public_net}'/>
      <model type='virtio'/>
      <alias name='net1'/>
      <address type='pci' domain='0x0000' bus='0x00' slot='0x04' function='0x0'/>
    </interface>
    <serial type='pty'>
      <source path='/dev/pts/6'/>
      <target port='0'/>
      <alias name='serial0'/>
    </serial>
    <console type='pty' tty='/dev/pts/6'>
      <source path='/dev/pts/6'/>
      <target type='serial' port='0'/>
      <alias name='serial0'/>
    </console>
    <input type='mouse' bus='ps2'/>
    <input type='keyboard' bus='ps2'/>
    <graphics type='vnc' port='5900' autoport='yes' listen='0.0.0.0'>
      <listen type='address' address='0.0.0.0'/>
    </graphics>
    <video>
      <model type='vga' vram='9216' heads='1'/>
      <alias name='video0'/>
      <address type='pci' domain='0x0000' bus='0x00' slot='0x02' function='0x0'/>
    </video>
    <memballoon model='virtio'>
      <alias name='balloon0'/>
      <address type='pci' domain='0x0000' bus='0x00' slot='0x0a' function='0x0'/>
    </memballoon>
  </devices>
</domain>
    """
    if admin:

        vcpu = cfg["ADMIN_CPU"]
        memory = cfg["ADMIN_RAM"] * 1024
        first_boot = "hd"
        second_boot = "cdrom"
        iso = """    <disk type='file' device='cdrom'>
      <driver name='qemu' type='raw' cache='unsafe'/>
      <source file='{iso_path}'/>
      <target dev='sdb' bus='ide' tray='open'/>
      <readonly/>
    </disk>""".format(iso_path=cfg["ISO_PATH"])

    else:

        vcpu = cfg["SLAVE_CPU"]
        memory = cfg["SLAVE_RAM"] * 1024
        first_boot = "hd"
        second_boot = "pxe"
        iso = ""

    admin_net = cfg["ADMIN_SUBNET"]
    public_net = cfg["PUBLIC_SUBNET"]
    hd_volume = vol_obj.path()

    xml = node_template_xml.format(
        name=name,
        vcpu=vcpu,
        memory=memory,
        first_boot=first_boot,
        second_boot=second_boot,
        hd_volume=hd_volume,
        iso=iso,
        admin_net=admin_net,
        public_net=public_net
    )

    print (xml)

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

    cfg["ISO_PATH"] = "/srv/iso/bulk"
    start_node(cfg["ENV_NAME"]+"_adm", admin=True)

    send_keys()

    wait_for_api_is_ready()

    start_slaves()

    configure_nailgun()

    wait_for_cluster_is_ready()

    db.close()

if __name__ == "__main__":
    main()
