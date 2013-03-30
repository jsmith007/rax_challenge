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
    parser.add_argument('-d', '--directory', help='Directory to upload', required=True)
    parser.add_argument('-c', '--container',  help='Container name to which upload', required=True)

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
    if not os.path.exists(args.directory):
        print "Invalid path: ", args.directory
        sys.exit(1)

    runAuth()

    cf = pyrax.cloudfiles

    print "Creating container ", args.container
    cont = cf.create_container(args.container)

    print "Beginning Folder Uplaod"
    upload_key, total_bytes = cf.upload_folder(args.directory, cont)
    print "Total bytes to upload: ", total_bytes
    uploaded = 0
    while uploaded < total_bytes:
        uploaded = cf.get_uploaded(upload_key)
        sys.stdout.write("\rProgress ")
        sys.stdout.write("{0}%\r".format(((uploaded * 100.0) / total_bytes)))
        sys.stdout.flush()
        sleep(1)
    print
    print "Name:", cont.name
    print "# of objects:", cont.object_count

if __name__ == "__main__":
    main()
