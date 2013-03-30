#!/usr/bin/env python

import os
import sys
import pyrax
import pyrax.exceptions as exc
import ConfigParser
import argparse
import getpass
from time import sleep

credFile = os.path.expanduser('~/.rackspace_cloud_credentials')
cdb = None

def parseArgs():
    parser = argparse.ArgumentParser()
    parser.add_argument('-i','--instancename', help='Database instance name')
    parser.add_argument('-s', '--instancesize', help='Database instance size')
    parser.add_argument('-d', '--database', help='Database to create')
    parser.add_argument('-u', '--username', help='Username to create')
    parser.add_argument('-p', '--password', help='Users password')

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
    global cdb
    cdb = pyrax.cloud_databases

    # user input
    instName = raw_input("Enter a name for your new instance: ")

    # flavor
    flavors = cdb.list_flavors()
    print
    print "Available Flavors:"
    for pos, flavor in enumerate(flavors):
        print "%s: %s, %s" % (pos, flavor.name, flavor.ram)
    flav = int(raw_input("Select a Flavor for your new instance: "))
    try:
        selected = flavors[flav]
    except IndexError:
        print "Invalid selection; exiting."
        sys.exit(2)
    print

    # instance size
    instSize = int(raw_input("Enter the volume size in GB (1-50): "))
    while (instSize < 1 and instSize > 50):
        instSize = int(raw_input("Enter the volume size in GB (1-50): "))

    dbName = raw_input("Enter the name of the new database to create in this instance: ")
    user = raw_input("Enter the user name: ")
    pword = getpass.getpass("Enter the password for this user: ")


    # build instance
    sys.stdout.write('Building instance ')
    sys.stdout.flush()
    dbInst = cdb.create(instName, flavor=selected, volume=instSize)
    dbStatus = cdb.get(dbInst.id)
    while (dbStatus.status == "BUILD"):
        sleep(15)
        sys.stdout.write('.')
        sys.stdout.flush()
        dbStatus = cdb.get(dbInst.id)
    sys.stdout.write(" Done\n")
    sys.stdout.flush()

    # build database
    print "Creating Database"
    db = dbInst.create_database(dbName)
    # create user
    print "Creating user"
    user = dbInst.create_user(user, pword, database_names=[db.name])

if __name__ == "__main__":
    main()
