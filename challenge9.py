#!/usr/bin/env python

import os
import sys
import pyrax
import pyrax.exceptions as exc
import ConfigParser
import argparse
import re
from time import sleep

credFile = os.path.expanduser('~/.rackspace_cloud_credentials')

def parseArgs():
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--fqdn',  help='FQDN for server', required=True)
    parser.add_argument('-i', '--image',  help='Image name or UUID for image', required=True)
    parser.add_argument('-f', '--flavor',  help='Flavor/memory size of server in numbers', required=True)
    parser.add_argument('-s', '--serverName',  help='Server Name')

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

    # get image list
    imageList = cs.images.list()
    imageListID = [image.id for image in imageList]
    if (args.image not in imageListID):
        print "%s is not an image id. Valid entries are:" % args.image
        print "\tID\t\t\t\t\tName"
        for img in imageList:
            print "%s\t%s" % (img.id, img.name)
        sys.exit(1)

    # get flavor list
    flavorList = cs.flavors.list()
    flavorID = None
    for flavor in flavorList:
        if str(flavor.ram) == args.flavor:
            flavorID = flavor.id
            break
    if flavorID == None:
        flavorListRam = [ str(flavor.ram) for flavor in flavorList ]
        print "%s is not a server flavor.  Valid entries are:" % args.flavor
        print "\n".join("%s"%flavor for flavor in flavorListRam)
        sys.exit(1)

    fqdnEntryData = args.fqdn.split('.')
    domainName = args.fqdn
    if (len(fqdnEntryData) > 2):
        domainName = fqdnEntryData[-2] + '.' + fqdnEntryData[-1]
        if (domainName == ".co.uk"):
            domainName = fqdnEntryData[-3] + '.' + fqdnEntryData[-2] + '.' + fqdnEntryData[-1]

    sys.stdout.write("Building server ")
    sys.stdout.flush()
    server = cs.servers.create(args.fqdn, args.image, flavorID)
    serverStatus = cs.servers.get(server.id)
    while (serverStatus.networks is None or len(serverStatus.networks) == 0):
        sys.stdout.write(".")
        sys.stdout.flush()
        sleep(5)
        serverStatus = cs.servers.get(server.id)
    print "Done!"
    print "Adding dns entry"

    cdns = pyrax.cloud_dns
    try:
        domain = cdns.find(name=domainName)
    except exc.NotFound:
        try:
            adminEmail = 'admin@' + domainName
            domain = cdns.create(name=domainName, emailAddress=adminEmail,ttl=900)
        except exc.DomainCreationFailed as e:
            print "Domain creation failed: ", e
    a_rec = {}
    if (serverStatus.accessIPv4 == "" or serverStatus.accessIPv4 == None):
        a_rec = {"type": "A",
            "name": args.fqdn,
            "data": serverStatus.networks['public'][0],
            "ttl": 300}
    else:
        a_rec = {"type": "A",
            "name": args.fqdn,
            "data": serverStatus.accessIPv4,
            "ttl": 300}
    record = domain.add_records([a_rec])

    print "Server data"
    print "Server Name: ", server.name
    print "Server ID: ", server.id
    print "Server IP: ", serverStatus.accessIPv4
    print "Server Admin Password: ", server.adminPass
    print "Server Status:", serverStatus.status

if __name__ == "__main__":
    main()
