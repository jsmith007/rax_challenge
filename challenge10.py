#!/usr/bin/env python

import os
import sys
import pyrax
import pyrax.exceptions as exc
import ConfigParser
import argparse
import re
from time import sleep
from subprocess import call

credFile = os.path.expanduser('~/.rackspace_cloud_credentials')
errorPageHtml = "<head><title>Error Sorry</title></head><body><H1>Tried FAILED</H1></body></html>"

serverBaseName = 'chal10-ServerNode'
lbBaseName = 'chal10_LB'
imageId = 'c195ef3b-9195-4474-b6f7-16e5bd86acd0' # CentOS 6.3
flavorId = 2  # 512MB Standard Instance

def parseArgs():
    parser = argparse.ArgumentParser()
    parser.add_argument('-s', '--sshkeyfile', help='File name containing SSH Key to upload at server build time')
    parser.add_argument('-f', '--fqdn', help='FQDN for the LB VIP', required=True)
    parser.add_argument('-c', '--containername', help='Cloud files container name in which to backup error file')
    parser.add_argument('-n', '--servername', help='Basename for cloud servers')
    parser.add_argument('-l', '--lbname', help='Load Balancer Name')

    namespace_args, extras = parser.parse_known_args()

    dnsDisallowed = re.compile("[^a-zA-Z\d\-\.]", re.IGNORECASE)
    if dnsDisallowed.search(namespace_args.fqdn):
        print "%s is not a valid Fully Qualified Domain Name"% namespace_args.fqdn
        sys.exit(1)
    fqdnEntryData = namespace_args.fqdn.split('.')
    if (len(fqdnEntryData) < 2):
        print "%s is not a Fully Qualified Domain Name."%namespace_args.fqdn
        sys.exit(1)

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

    cs = pyrax.cloudservers
    clb = pyrax.cloud_loadbalancers
    cdns = pyrax.cloud_dns

    
    print "Creating servers."
    serverName = serverBaseName
    if (args.servername):
        serverName = args.servername

    metadata = {"built_from": "rax_code_challenge10"}
    rsaKeyFileName = 'challenge10_id_rsa'
    rsaKeyFileNamePub = None
    userKey = False

    if (args.sshkeyfile):
        rsaKeyFileName = args.sshkeyfile
        rsaKeyFileNamePub = args.sshkeyfile
        userKey = True
    else:
        rsaKeyFileNamePub = rsaKeyFileName + '.pub'
        sshKeyGenCmd = "ssh-keygen -t rsa -f " + rsaKeyFileName + " -P ''"
        call(sshKeyGenCmd, shell = True)
    with open(rsaKeyFileNamePub, 'r') as content_file:
            sshPubKey = content_file.read()
    buildFiles = {"/root/.ssh/authorized_keys": sshPubKey}
    sys.exit()
    server1 = cs.servers.create(str(serverName+'1'), imageId, flavorId, meta=metadata, files = buildFiles)
    server2 = cs.servers.create(str(serverName+'2'), imageId, flavorId, meta=metadata, files = buildFiles)

    server1Status = cs.servers.get(server1.id)
    server2Status = cs.servers.get(server2.id)

    sys.stdout.write("Waiting for servers and load balancer to build ")
    sys.stdout.flush()

    while not (('private' in server1Status.addresses) and ('private' in server2Status.addresses)):
        sleep(5)
        sys.stdout.write('.')
        sys.stdout.flush()
        server1Status = cs.servers.get(server1.id)
        server2Status = cs.servers.get(server2.id)

    node1 = clb.Node(address=str(server1Status.addresses['private'][0]['addr']), port=80, condition="ENABLED")
    node2 = clb.Node(address=str(server2Status.addresses['private'][0]['addr']), port=80, condition="ENABLED")

    vip = clb.VirtualIP(type="PUBLIC")
    if (args.lbname):
        lbName = args.lbname
    else:
        lbName = lbBaseName
    lb = clb.create(lbName, port=80, protocol="HTTP", nodes=[node1, node2],virtual_ips=[vip])

    serversReady = False
    lbReady = False
    lbStatus = None
    while not serversReady and not lbReady:
    # wait for both servers to be completed building
        sys.stdout.write('.')
        sys.stdout.flush()
        server1Status = cs.servers.get(server1.id)
        server2Status = cs.servers.get(server2.id)
        if (('private' in server1Status.addresses) and ('private' in server2Status.addresses)):
            serversReady = True
        lbStatus = clb.get(lb.id)
        if lbStatus.status == "ACTIVE":
            lbReady = True
        sleep(15)

    sys.stdout.write(" DONE!\n")
    sys.stdout.flush()

    print "Setting and backing up error page"
    pyrax.utils.wait_until(lbStatus, "status", "ACTIVE", interval=1, attempts=30)
    lbStatus.add_health_monitor(type="HTTP", statusRegex="^[234][0-9][0-9]$", bodyRegex="^<html>")
    pyrax.utils.wait_until(lbStatus, "status", "ACTIVE", interval=1, attempts=30)
    lbStatus.set_error_page(errorPageHtml)

    cf = pyrax.cloudfiles
    containerName = 'challenge10_backup'
    if (args.containername):
        containerName = args.containername

    errorFileName = 'error.html'
    container = cf.create_container(containerName)
    container.make_public(ttl=1200)

    with file(errorFileName, "w") as tmp:
        tmp.write(errorPageHtml)
    cf.upload_file(container, errorFileName, content_type="text/text")
    os.unlink(errorFileName)

# create dns entry for fqdn
    fqdnEntryData = args.fqdn.split('.')
    domainName = args.fqdn
    if (len(fqdnEntryData) > 2):
        domainName = fqdnEntryData[-2] + '.' + fqdnEntryData[-1]
        if (domainName == ".co.uk"):
            domainName = fqdnEntryData[-3] + '.' + fqdnEntryData[-2] + '.' + fqdnEntryData[-1]

    try:
        domain = cdns.find(name=domainName)
    except exc.NotFound:
        try:
            adminEmail = 'admin@' + domainName
            if(args.adminemail):
                adminEmail = args.adminemail

            domain = cdns.create(name=domainName, emailAddress=adminEmail,ttl=900)
        except exc.DomainCreationFailed as e:
            print "Domain creation failed: ", e
    a_rec = {"type": "A",
            "name": args.fqdn,
            "data": lb.virtual_ips[0].address,
            "ttl": 300}
    record = domain.add_records([a_rec])
    server1Status = cs.servers.get(server1.id)
    server2Status = cs.servers.get(server2.id)

    print "#########################################"
    print "#"
    print "# SSH Key public: ", rsaKeyFileNamePub
    if not userKey:
        print "# SSH Key private: ", rsaKeyFileName
    print "#"
    print "# Server1 Name: ", server1.name
    print "# Server1 ID: ", server1.id
    print "# Server1 IP: ", server1Status.addresses['public'][1]['addr']
    print "# Server1 Admin Password: ", server1.adminPass
    print "# Server1 Status:", server1Status.status
    print "#"
    print "# Server2 Name: ", server2.name
    print "# Server2 ID: ", server2.id
    print "# Server2 IP: ", server2Status.addresses['public'][1]['addr']
    print "# Server2 Admin Password: ", server2.adminPass
    print "# Server2 Status:", server2Status.status
    print "#"
    print "# Cloud File Container for backup: ", containerName
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
