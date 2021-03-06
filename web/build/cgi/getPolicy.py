#!/usr/bin/env python

import sys
import os
import cgi
import json
import ConfigParser
import sqlite3
import requests


def usage():
    '''Function describing the script usage
    '''
    print "Script to get the policy from the database"
    print "Usage: getPolicy.py"
    print "Options:"
    print "help=help                 Prints this help"
    print ""


def getData(config, uuid):
    '''Function to get the policy from the database
    '''

    # TODO: This function needs to change we need to use the uuid to do the
    # XPATH query to get the policy.

    # Create the URL for the policy xml file
    policy_url = config.get("XMLDATABASE", "name") + "/policy_%s.xml" % uuid
    response = requests.get(policy_url,
                            auth=(config.get("XMLDATABASE", "user"),
                                  config.get("XMLDATABASE", "pass")))

    if response.status_code == 200:
        policy = response.text
    else:
        print "Problem fetching the policy from the database: ",\
            response.status_code
        print response.text
        sys.exit(response.status_code)

    # get the uuid key and the policy key
#    uuid_key = config.get("POLICY_SCHEMA", "uniqueid")
#    policy_key = config.get("POLICY_SCHEMA", "object")

    # Open the database
#    dbfile = config.get("DATABASE", "name").strip()
#    if (not os.path.isfile(dbfile)):
#        sys.stderr.write("Problem opening the database: %s" % dbfile)

    # Get the uuid key corresponding to the uuid and construct
    # the policy key
#    conn = sqlite3.connect(dbfile)
#    cur = conn.cursor()
#    cur.execute("select key from policies where key like ? and value = ?",
#                ("%s%%" % uuid_key, uuid))
#    result = cur.fetchone()
#    pol_index = result[0].split("_")[-1]
#    policy_key = "%s_%s" % (policy_key, pol_index)
#    cur.execute("select value from policies where key = ?",
#                (policy_key,))
#    policy = cur.fetchone()[0]

    # policy = policy.replace("\n", "<br/>")
    print "Content-Type: application/json charset=utf-8"
    print ""
    print json.dumps(policy)

if __name__ == '__main__':
    cfgfile = "./config/policy.cfg"

    fields = cgi.FieldStorage()

    if ("help" in fields):
        usage()
        sys.exit()

    # Get the uuid
    uuid = fields["uuid"].value

    # Read the configs
    config = ConfigParser.ConfigParser()
    config.read(cfgfile)

    getData(config, uuid)
