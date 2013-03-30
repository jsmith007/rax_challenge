#!/usr/bin/env python

import os
import sys
import pyrax
import pyrax.exceptions as exc
import ConfigParser
import argparse
import datetime
import dumper
from time import sleep

credFile = os.path.expanduser('~/.rackspace_cloud_credentials')
cs = None
sleepTime = 15

def parseArgs():
    parser = argparse.ArgumentParser()
    parser.add_argument('-n', '--name', help='Name of server to clone')
    parser.add_argument('-i', '--id',  help='Id of server to clone')
    parser.add_argument('-c', '--clonename', help='Name to get the new server from the image')

    parsedArgs, extras = parser.parse_known_args()
    if (parsedArgs.name is None and parsedArgs.id is None):
        print "Option id or name is required"
        sys.exit(1)
    return parsedArgs

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

def createServerImage(server):
    if (server is None):
        print "Error calling createServerImage: No server object passed"
        sys.exit(2)
    imageName = server.name + '_' + datetime.datetime.now().strftime('%Y%m%d_%H%M')
    imageUUID = server.create_image(imageName)
    print "Creating %s image %s " % (server.name, imageName)
    return imageUUID

def monitorImageBuild(imageId,serverObj):
    if (imageId is None):
        print "Error calling monitorImageBUild: No image id passed"
        sys.exit(2)
    if (serverObj is None):
        print "Error calling monitorImageBUild: No server object passed"
        sys.exit(2)

    print "Monitoring Image %s for completion" % imageId
    lastPercentage = 0
    curServer = cs.servers.get(serverObj.id)
    sys.stdout.write("wait ")
    sys.stdout.flush()
    while (curServer._info['OS-EXT-STS:task_state'] == 'image_snapshot'):
        sys.stdout.write(".")
        sys.stdout.flush()
        sleep(sleepTime)
        curServer = cs.servers.get(serverObj.id)

    print " done"

def buildServerFromImage(imageId,newServerName,flavorId):
    if (imageId is None):
        print "Error calling buildServerFromImage: No image id passed"
        sys.exit(2)
    if (newServerName is None):
        print "Error calling buildServerFromImage: No server name passed"
        sys.exit(2)
    sys.stdout.write('Building server .')
    sys.stdout.flush()
    newServer = cs.servers.create(newServerName, imageId, flavorId)
    serverStatus = newServer
    while (serverStatus.status != "ACTIVE"):
        sleep(sleepTime)
        sys.stdout.write('.')
        sys.stdout.flush()
        serverStatus = cs.servers.get(newServer.id)
    sys.stdout.write(" done\n")
    sys.stdout.flush()
    print "Server Name: %s\nServer ID: %s\nIP Address: %s\nAdmin Password: %s" % (newServer.name,newServer.id,serverStatus.accessIPv4,newServer.adminPass)


def main():
    args = parseArgs()
    runAuth()
    global cs
    cs = pyrax.cloudservers
    fullServerList = cs.servers.list()
    server = None
    srv_by_name = {}
    srv_by_id = {}
    for srv in fullServerList:
        srv_by_name[srv.name] = srv
        srv_by_id[srv.id] = srv

    type = None
    input = None
    try:
        if (args.id is not None):
            type = 'id'
            input = args.id
            server = srv_by_id[args.id]
        elif (args.name is not None):
            type = 'name'
            input = args.name
            server = srv_by_name[args.name]
        else:
            print "should not get here"
            sys.exit(2)
    except:
        pass
    
    if (server is None):
        print "No server found with %s: %s" % (type, input)
        sys.exit(1)
    serverImageID = createServerImage(server)
    monitorImageBuild(serverImageID,server)

    cloneName = args.clonename
    if (cloneName is None):
        cloneName = server.name + '_clone'
    buildServerFromImage(serverImageID,cloneName,server.flavor['id'])


if __name__ == "__main__":
    main()
