#!/usr/bin/env python

import os
import sys
import pyrax
import pyrax.exceptions as exc
import ConfigParser
import argparse
from time import sleep

credFile = os.path.expanduser('~/.rackspace_cloud_credentials')
cs = None
clb = None
serverBaseName = 'chal7-node'
lbBaseName = 'chal7-lb'
imageId = 'c195ef3b-9195-4474-b6f7-16e5bd86acd0' # CentOS 6.3
flavorId = 2  # 512MB Standard Instance

def parseArgs():
    parser = argparse.ArgumentParser()
    parser.add_argument('-n', '--servername', help='Name of server to create')
    parser.add_argument('-l', '--lbname',  help='Name of the load balancer to create')

    namespace_args, extras = parser.parse_known_args()
    return namespace_args

def runAuth():
    # import creds from file
    
    raxCreds = ConfigParser.RawConfigParser()
    raxCreds.read(credFile)
    if len(raxCreds.sections()) < 1:
        print "No configuration found"
        sys.exit(0)

    # get credentials from config file
    username = raxCreds.get(raxCreds.sections()[0],'username')
    key = raxCreds.get(raxCreds.sections()[0],'api_key')

    try:
        pyrax.set_credentials(username,key)
    except exc.AuthenticationFailed:
        print "Did you remember to replace the credentials with your actual username and api_key?"
        print "authenticated =", pyrax.identity.authenticated
        print

def main():
    args = parseArgs()
    runAuth()

    global cs
    global clb
    global serverBaseName
    global lbBaseName
    cs = pyrax.cloudservers
    clb = pyrax.cloud_loadbalancers

    sys.stdout.write("Creating servers ")
    sys.stdout.flush()
    if (args.servername):
        serverBaseName = args.servername

    server1 = cs.servers.create(str(serverBaseName+'1'), imageId, flavorId)
    server2 = cs.servers.create(str(serverBaseName+'2'), imageId, flavorId)
    server1Status = None
    server2Status = None
    
    serversReady = False
    while not serversReady:
    # wait for both servers to be completed building
        sys.stdout.write('.')
        sys.stdout.flush()
        sleep(15)
        server1Status = cs.servers.get(server1.id)
        server2Status = cs.servers.get(server2.id)
        if (('private' in server1Status.addresses) and ('private' in server2Status.addresses)):
            serversReady = True

    sys.stdout.write(" done\nCreating load balander and adding nodes ")
    sys.stdout.flush()

    node1 = clb.Node(address=str(server1Status.addresses['private'][0]['addr']), port=80, condition="ENABLED")
    node2 = clb.Node(address=str(server2Status.addresses['private'][0]['addr']), port=80, condition="ENABLED")
    vip = clb.VirtualIP(type="PUBLIC")
    
    if (args.lbname):
        lbName = args.lbname
    else:
        lbName = lbBaseName
    lb = clb.create(lbName, port=80, protocol="HTTP", nodes=[node1,node2],virtual_ips=[vip])
    lbStatus = clb.get(lb.id)
    while lbStatus.status == "BUILD":
        sys.stdout.write('.')
        sys.stdout.flush()
        sleep(5)

    print "#########################################"
    print "# Server1 Name: ", server1.name
    print "# Server1 ID: ", server1.id
    print "# Server1 IP: ", server1Status.accessIPv4
    print "# Server1 Admin Password: ", server1.adminPass
    print "# Server1 Status:", server1Status.status
    print "#"
    print "# Server2 Name: ", server2.name
    print "# Server2 ID: ", server2.id
    print "# Server2 IP: ", server2Status.accessIPv4
    print "# Server2 Admin Password: ", server2.adminPass
    print "# Server2 Status:", server2Status.status
    print "#"
    print "# Load Balancer Name: ", lb.name
    print "# Load Balancer ID: ", lb.id
    print "# Load Balancer VIP: ", lb.virtual_ips[0].address
    print "# Load Balancer Algorithm: ", lb.algorithm
    print "# Load Balancer Protocol: ", lb.protocol
    print "# Load Balancer Status: ", lb.status
    print "#########################################"

if __name__ == "__main__":
    main()
