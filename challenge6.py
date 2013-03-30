#!/usr/bin/env python

import os
import sys
import pyrax
import pyrax.exceptions as exc
import ConfigParser
import argparse
from time import sleep

credFile = os.path.expanduser('~/.rackspace_cloud_credentials')

def parseArgs():
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--containername', help='Cloud files container name', required=True)
    parser.add_argument('-t', '--ttl', help='Cloud files container ttl')

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

    cf = pyrax.cloudfiles

    container = cf.create_container(args.containername)
    ttlValue = 1200
    if (args.ttl):
        ttlValue = args.ttl
    container.make_public(ttl=ttlValue)

    print "Cloud files CDN Enabled Container"
    print "cdn_enabled", container.cdn_enabled
    print "cdn_ttl", container.cdn_ttl
    print "cdn_log_retention", container.cdn_log_retention
    print "cdn_uri", container.cdn_uri
    print "cdn_ssl_uri", container.cdn_ssl_uri
    print "cdn_streaming_uri", container.cdn_streaming_uri

if __name__ == "__main__":
    main()
