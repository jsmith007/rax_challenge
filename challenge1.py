#!/usr/bin/env python

import os
import sys
import pyrax
import pyrax.exceptions as exc
import ConfigParser
from time import sleep

credFile = os.path.expanduser('~/.rackspace_cloud_credentials')
serverBaseName = 'cloud_jason_Web'
imageId = 'c195ef3b-9195-4474-b6f7-16e5bd86acd0' # CentOS 6.3
flavorId = 2  # 512MB Standard Instance
numServers = 3

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

def main():
    runAuth()

    cs = pyrax.cloudservers
    serverObjs = {}
    serverList = []
    for itr in range(1,(numServers+1)):
        serverName = serverBaseName + str(itr)
        print "Creating server number %s with name %s" % (itr, serverName)
        # set flavor and size
        # do function call to create server
        # add server name and id into dict
        server = cs.servers.create(serverName, imageId, flavorId)
        serverObjs[server.id] = server
        serverList.append(server.id)
    print "Please wait while we get the network information"
    while (len(serverList) > 0):
        sleep(15)
        for serverId in serverList:
            serverStatus = cs.servers.get(serverId)
            if ( serverStatus.networks is not None and len(serverStatus.networks) > 0):
                print serverObjs[serverId].name
                print "ID: ", serverStatus.id
                print "Admin password: ", serverObjs[serverId].adminPass
                print "Public IPv4 address: " , serverStatus.networks['public'][0]
                print "Public IPv6 address: " , serverStatus.networks['public'][1]
                serverList.remove(serverId)

if __name__ == "__main__":
    main()
