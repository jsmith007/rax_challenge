#!/usr/bin/env python

import os
import sys
import pyrax
import pyrax.exceptions as exc
import ConfigParser
import argparse
import re

credFile = os.path.expanduser('~/.rackspace_cloud_credentials')
regex_FQDN = "(?=^.{1,254}$)(^(?:(?!\d+\.)[a-zA-Z0-9_\-]{1,63}\.?)+(?:[a-zA-Z]{2,})$)"
regex_IPV4 = "(?=^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$)"


def parseArgs():
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--fqdn', help='Fully Qualified Domain Name',required=True)
    parser.add_argument('-i', '--ipaddress', help='IP Address', required=True)
    parser.add_argument('-e','--domainemail', help='Domain Email if needed')

    namespace_args, extras = parser.parse_known_args()
    if (not re.search(regex_FQDN,namespace_args.fqdn)):
        print "FQDN is not valid try again"
        sys.exit(1)
    if (not re.search(regex_IPV4,namespace_args.ipaddress)):
        print "IP ADDRESS  is not valid try again"
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
    reSearch = re.search("([^\.\s]+\.[^\.\s]+$)",args.fqdn)
    targetDomain = reSearch.groups()[0]
    runAuth()
    cdns = pyrax.cloud_dns
    
    allDomains = cdns.get_domain_iterator()
    domainExists = False
    domain = None
    for domain in allDomains:
        if (domain.name ==  targetDomain):
            domainExists = True
            break
    if (not domainExists):
        # create domain
        print "Creating domain for ", targetDomain
        if (args.domainemail):
            domainEmail = args.domainemail
        else:
            domainEmail = 'admin@' + targetDomain
        try:
            domain = cdns.create(name=targetDomain,emailAddress=domainEmail,ttl=900)
        except exc.DomainCreationFailed as e:
            print "Domain creation failed: ", e
            sys.exit(1)
    print "Adding record for ", args.fqdn
    recs = [{
        "type": "A",
        "name": str(args.fqdn),
        "data": str(args.ipaddress),
        "ttl": 600
        }]
    try:
        addedRecs = cdns.add_records(domain,recs)
        print "Successfully added record " , args.fqdn
    except:
        print "Failed to add record ", args.fqdn


if __name__ == "__main__":
    main()
