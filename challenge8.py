#!/usr/bin/env python

import os
import sys
import pyrax
import pyrax.exceptions as exc
import ConfigParser
import argparse
import pyrax.utils as utils
from time import sleep

credFile = os.path.expanduser('~/.rackspace_cloud_credentials')
indexFileText = "<html><head><title>CDN Page</title></head><body>Welcome to the CDN.</body></html>"

def parseArgs():
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--containername', help='Name to give cloud files container')
    parser.add_argument('-d', '--dnsentry',  help='CNAME entry to add for the container  path', required=True)
    parser.add_argument('-e', '--adminemail', help = 'Admin email if needed')

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
#    """Write a script that will create a static webpage served out of Cloud Files. The script must
#    create a new container, cdn enable it, enable it to serve an index file, create an index file
#    object, upload the object to the container, and create a CNAME record pointing to the CDN URL of the
#    container. """
    # cloud container file with cdn

    cf = pyrax.cloudfiles
    containerName = pyrax.utils.random_name()
    if (args.containername):
        containerName = args.containername

    indexFileName = 'index.html'
    container = cf.create_container(containerName)
    container.make_public(ttl=1200)
                               
    # create index.html and upload to container
    #with utils.SelfDeletingTempfile() as indexFileName:
    with file(indexFileName, "w") as tmp:
        tmp.write(indexFileText)
    print "Uploading file: ", indexFileName
    print "Container name: ", containerName
    print "index file name: ", indexFileName
    cf.upload_file(container, indexFileName, content_type="text/text")
    os.unlink(indexFileName)

    print "Cloud files CDN Enabled Container"
    print "cdn_enabled", container.cdn_enabled
    print "cdn_ttl", container.cdn_ttl
    print "cdn_log_retention", container.cdn_log_retention
    print "cdn_uri", container.cdn_uri
    print "cdn_ssl_uri", container.cdn_ssl_uri
    print "cdn_streaming_uri", container.cdn_streaming_uri

    # create a cname record for the cdn url
    cdns = pyrax.cloud_dns
    
    entryData = args.dnsentry.split('.')
    domainName = args.dnsentry
    if (len(entryData) > 2):
        domainName = entryData[-2] + '.' + entryData[-1]
        if (domainName == ".co.uk"):
            domainName = entryData[-3] + '.' + entryData[-2] + '.' + entryData[-1]

    try:
        domain = cdns.find(name=domainName)
    except exc.NotFound:
        try:
            adminEmail = 'admin@' + domainName
            if(args.adminemail):
                adminEmail = args.adminemail

            domain = cdns.create(name=domainName, emailAddress=adminEmail,tty=900)
        except exc.DomainCreationFailed as e:
            print "Domain creation failed: ", e
    cname_rec = {"type": "CNAME",
            "name": args.dnsentry,
            "data":container.cdn_uri,
            "ttl": 300}
    record = domain.add_records([cname_rec])

    print "Created CNAME record for %s pointing to %s" % (record[0].name, record[0].data)
if __name__ == "__main__":
    main()
