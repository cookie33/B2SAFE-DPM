#!/usr/bin/env python
import json
import sys
import ConfigParser
import StringIO
import hashlib
import time
import os
import sqlite3

sys.path.append(os.path.dirname(os.path.realpath(sys.argv[0])))
import policy_irods_sub
import policy_irods_lib
import policy_lib


class Policy():
    '''policy class'''
    def __init__(self, config):
        '''initialiser'''
        self.uuid = None
        self.policy = {}
        self.config = config
        self.dateType = 'date'
        self.periodicType = 'period'
        self.irodsSystem = 'iRODS'
        self.irodsNamespace = "irodsns:coordinates"
        # Check the database exists - if not create it
        conn = sqlite3.connect(config.get("DATABASE", "name").strip())
        cur = conn.cursor()
        cur.execute('''create table if not exists policies (key text, value
                text)''')
        conn.commit()

    def processForm(self, formdata):
        '''process the form data and fill the object attributes
        '''
        trigger_val = ''
        self.policy[self.config.get('POLICY_SCHEMA',
                    'removed').strip()] = 'false'
        self.policy[self.config.get('POLICY_SCHEMA',
                    'community').strip()] = formdata['community']
        self.policy[self.config.get('POLICY_SCHEMA',
                    'uniqueid').strip()] = formdata['uuid']
        self.policy[self.config.get('POLICY_SCHEMA',
                    'id').strip()] = formdata['id']
        self.policy[self.config.get('POLICY_SCHEMA',
                    'name').strip()] = formdata['name']
        self.policy[self.config.get('POLICY_SCHEMA',
                    'version').strip()] = formdata['version']
        self.policy[self.config.get('POLICY_SCHEMA',
                    'author').strip()] = formdata['author']
        self.policy[self.config.get('ACTIONS_SCHEMA',
                    'type').strip()] = formdata['type']['name']
        if (formdata['trigger']['name'] == self.dateType):
            trigger_val = formdata['trigger_date']
        elif (formdata['trigger']['name'] == self.periodicType):
            trigger_val = "%s, %s, %s, %s, %s" %\
                (formdata['trigger_period']['minute']['name'],
                 formdata['trigger_period']['hour']['name'],
                 formdata['trigger_period']['day']['name'],
                 formdata['trigger_period']['month']['name'],
                 formdata['trigger_period']['weekday']['name'])
        self.policy[self.config.get('ACTIONS_SCHEMA',
                    'trigger').strip()] = trigger_val
        self.policy[self.config.get('ACTIONS_SCHEMA',
                    'trigger_type').strip()] = \
            formdata['trigger']['name'].strip()
        self.policy[self.config.get('ACTIONS_SCHEMA', 'name').strip()] =\
            formdata['action']['name']

        col_idx = 0
        col_idx2 = 0
        for acoll in formdata['collections']:
            akeytype = "%s_%s" % (self.config.get('DATASETS_SCHEMA',
                                                  'type').strip(), col_idx)
            akeypid = "%s_%s" % (self.config.get('DATASETS_SCHEMA',
                                 'pid').strip(), col_idx)
            src_site = "%s_%s" % (self.config.get('SOURCES_SCHEMA',
                                  'site'), col_idx2)
            src_org = "%s_%s" % (self.config.get('SOURCES_SCHEMA',
                                                 'site_type'),
                                 col_idx2)
            src_system = "%s_%s" % (self.config.get('SOURCES_SCHEMA',
                                                    'type'), col_idx2)
            src_resource = "%s_%s" % (self.config.get('SOURCES_SCHEMA',
                                                      'resource'),
                                      col_idx2)
            src_path = "%s_%s" % (self.config.get('SOURCES_SCHEMA',
                                  'path'), col_idx2)
            self.policy[akeytype] = None
            self.policy[akeypid] = None
            self.policy[src_site] = None
            self.policy[src_org] = None
            self.policy[src_resource] = None
            self.policy[src_path] = None
            self.policy[src_system] = None

            if (acoll['type']['name'] == 'pid'):
                self.policy[akeytype] = acoll['type']['name']
                self.policy[akeypid] = acoll['name']
                col_idx += 1
            elif (acoll['type']['name'] == 'collection'):
                scoll = formdata['sources'][col_idx2]
                self.policy[src_site] = scoll['site']['name']
                self.policy[src_org] = scoll['organisation']['name']
                self.policy[src_resource] = scoll['resource']['name']
                self.policy[src_path] = scoll['path']
                self.policy[src_system] = scoll['system']['name']
                self.policy[akeytype] = acoll['type']['name']
                col_idx2 += 1

        self.policy[self.config.get('TARGETS_SCHEMA',
                    'path').strip()] = formdata['target']['path']
        self.policy[self.config.get('TARGETS_SCHEMA', 'site').strip()] = \
            formdata['target']['site']['name']
        self.policy[self.config.get('TARGETS_SCHEMA', 'resource').strip()] = \
            formdata['target']['resource']['name']
        self.policy[self.config.get('TARGETS_SCHEMA', 'site_type').strip()] = \
            formdata['target']['organisation']['name']
        self.policy[self.config.get('TARGETS_SCHEMA', 'type').strip()] = \
            formdata['target']['system']['name']
#        self.policy[self.config.get('TARGETS_SCHEMA', 'loctype').strip()] = \
#            formdata['target']['loctype']['name']

    def createXML(self, formdata):
        '''Method to create an XML policy
        '''
        # Create instances of the classes generated from the schema
        # and fill the attributes and values. Need to start from the
        # inner node to the outer node

        # Build the dataset node
        xml_dataset = policy_lib.datasetType2()
        xml_dataset.collection = self.__createColls(formdata)

        # Build the action nodes
        xml_actions = policy_lib.actionsType()
        xml_actions.action = self.__createActions(formdata)

        # Build the policy node
        xml_pol = policy_lib.policy()
        xml_pol.uniqueid = formdata['uuid']
        xml_pol.version = formdata['version']
        xml_pol.name = formdata['name']
        xml_pol.author = formdata['author']
        xml_pol.dataset = xml_dataset
        xml_pol.actions = xml_actions

        # Output XML and store in key-value
        output = StringIO.StringIO()
        xml_pol.export(output, 0, namespacedef_=self.config.get(
            "XML_NAMESPACE", "namespacedef"))

        self.policy[self.config.get('POLICY_SCHEMA', 'object').strip()] = \
            output.getvalue()

    def __createActionType(self, formdata):
        '''Private method to build the action type node
        '''
        xml_action_type = policy_lib.actionType()
        # xml_action_type.policyID = formdata[]
        xml_action_type.valueOf_ = formdata['type']['name']
        return xml_action_type

    def __createTrigger(self, formdata):
        '''Private method to build the trigger node
        '''
        trigger_val = ''
        dateSpecified = False
        xml_trigger = policy_lib.triggerType()
        xml_trigger_action = policy_lib.actionType()

        # Process the form data according to the type selected
        if (formdata['trigger']['name'] == self.dateType):
            # The date is in the wrong format according to XML schema
            # it should be: secs mins hours day month year
            trigger_tmp = formdata['trigger_date'].split("-")
            trigger_val = "0 0 0 %s %s %s" % (trigger_tmp[2],
                                              trigger_tmp[1], trigger_tmp[0])
            dateSpecified = True
        elif (formdata['trigger']['name'] == self.periodicType):
            trigger_val = "%s %s %s %s %s" %\
                (formdata['trigger_period']['minute']['name'],
                 formdata['trigger_period']['hour']['name'],
                 formdata['trigger_period']['day']['name'],
                 formdata['trigger_period']['month']['name'],
                 formdata['trigger_period']['weekday']['name'])
            dateSpecified = True

        if (dateSpecified):
            xml_trigger.time = trigger_val
        else:
            xml_trigger_action.valueOf_ = trigger_val
            xml_trigger.action = xml_trigger_action
        return xml_trigger

    def __createActions(self, formdata):
        '''Private method to build the action nodes
        '''
        xml_actions = []
        # We could potentially have many actions so will need to
        # loop in the future
        xml_action = policy_lib.actionType1()
        xml_action.trigger = self.__createTrigger(formdata)
        xml_action.type_ = self.__createActionType(formdata)

        xml_targets = policy_lib.targetsType()
        xml_targets.target = self.__createTargets(formdata)
        xml_action.targets = xml_targets
        xml_action.name = formdata['action']['name']
        xml_actions.append(xml_action)
        return xml_actions

    def __createTgtLocation(self, formdata):
        '''Private method to build the location node
        '''
        xml_location = policy_irods_sub.coordinatesSub()
        xml_location.site = self.__createSite(formdata)
        xml_location.resource = formdata['target']['resource']['name']
        xml_location.path = formdata['target']['path']
        # Needed as the default location is abstract
        if (formdata['target']['system']['name'] == self.irodsSystem):
            xml_location.extensiontype_ = self.irodsNamespace
        return xml_location

    def __createSrcLocation(self, formdata, idx):
        '''Private method to build the location node
        '''
        xml_location = policy_irods_sub.coordinatesSub()
        xml_location.site = self.__createSite(formdata, idx)
        xml_location.resource = formdata['sources'][idx]['resource']['name']
        xml_location.path = formdata['sources'][idx]['path']
        # Needed as the default location is abstract
        if (formdata['sources'][idx]['system']['name'] == self.irodsSystem):
            xml_location.extensiontype_ = self.irodsNamespace
        return xml_location

    def __createSite(self, formdata, idx=-1):
        '''Private method to build the site node
        '''
        if (idx < 0):
            xml_site = policy_irods_sub.siteType2Sub()
            xml_site.type_ = formdata['target']['organisation']['name']
            xml_site.valueOf_ = formdata['target']['site']['name']
        else:
            xml_site = policy_irods_sub.siteType2Sub()
            xml_site.type_ = formdata['sources'][idx]['organisation']['name']
            xml_site.valueOf_ = formdata['sources'][idx]['site']['name']
        return xml_site

    def __createTargets(self, formdata):
        '''Private method to build the target nodes
        '''
        xml_targets = []
        # Currently we don't have more than one target so we just
        # use that.
        xml_target = policy_lib.locationPoint()
        xml_target.location = self.__createTgtLocation(formdata)
        xml_targets.append(xml_target)
        return xml_targets

    def __createColls(self, formdata):
        '''Private method to fill the collections
        '''
        xml_collections = []
        col_idx = 0
        for acoll in formdata['collections']:
            xml_collection = policy_lib.locationPoint()
            if (acoll['type']['name'] == 'pid'):
                xml_persistentIdentifier = \
                    policy_lib.persistentIdentifierType7()
                xml_persistentIdentifier.valueOf_ = acoll['name']
                xml_persistentIdentifier.type_ = acoll['type']['name']
            elif (acoll['type']['name'] == 'collection'):
                xml_source_location = self.__createSrcLocation(formdata,
                                                               col_idx)

            xml_collection.id = col_idx
            if (acoll['type']['name'] == 'pid'):
                xml_collection.persistentIdentifier = xml_persistentIdentifier
            elif (acoll['type']['name'] == 'collection'):
                xml_collection.location = xml_source_location
            xml_collections.append(xml_collection)
            col_idx += 1
        return xml_collections

    def setmd5(self, md5):
        '''Method to store the md5 hash
        '''
        self.policy[self.config.get("POLICY_SCHEMA", "md5").strip()] =\
            md5

    def settime(self, ctime):
        '''Method to set the create time
        '''
        self.policy[self.config.get("POLICY_SCHEMA", "ctime").strip()] = \
                ctime

def policyExists(pol, config):
    '''Function to check if the policy exists in the database by comparing
    checksums
    '''
    exists = False

    polmd5 = pol[config.get("POLICY_SCHEMA", "md5")]
    dbfile = config.get("DATABASE", "name").strip()

    # Open the database
    if (not os.path.isfile(dbfile)):
        sys.stderr.write("Database %s does not exist" % dbfile)
        sys.exit(-100)

    conn = sqlite3.connect(dbfile)
    cur = conn.cursor()

    # Check if the md5 exists in the database
    cur.execute('''select key from policies where value = ?''',
            (polmd5,))
    results = cur.fetchall()
    conn.commit()
    if (len(results) > 0):
        exists = True
    return exists

def dumpToKVDb(pol, config):
    '''Function to dump the policy to a key-value pair database
    '''
    dbfile = config.get("DATABASE", "name").strip()
    # Open the database
    if (not os.path.isfile(dbfile)):
        sys.stderr.write("Database %s does not exist" % dbfile)
        sys.exit(-100)

    conn = sqlite3.connect(dbfile)
    cur = conn.cursor()

    # get the last index from the database
    last_index = config.get("DATABASE", "last_index").strip()
    cur.execute('''select value from policies where key = ?''', (last_index,))
    results = cur.fetchall()
    if (len(results) > 0):
        next_index = int(results[0][0]) + 1
    else:
        next_index = 0

    # Write the key-value pairs to the db
    for akey in pol.keys():
        key = "%s_%s" %(akey, next_index)
        try:
            cur.execute('''insert into policies (key, value) values (?, ?)''',
                    (key, pol[akey]))
        except sqlite3.DatabaseError as er:
            sys.stderr.write("unable to write to db: ", er.message)
    # update the last index
    try:
        cur.execute("select value from policies where key = ?",
                ("last_index",))
        res = cur.fetchall()
        if (len(res) == 0):
            cur.execute('''insert into policies (key, value)
                values (?,?)''', ("last_index", next_index))
        else:
            cur.execute('''update policies set value = ? where key = ?''',
                    (next_index, "last_index"))

    except sqlite3.DatabaseError as er:
        sys.stderr.write("unable to write last index to db: ", er.message)

    conn.commit()

def runStore():
    # Get the schema used for the key-value pair database
    config = ConfigParser.ConfigParser()
    config.read("./config/policy.cfg")
    policy_exists = False

    # Read in the form data
    aform = json.load(sys.stdin)

    print "Content-Type: application/json\n"

    # Process the form data and create policy
    aPolicy = Policy(config)
    aPolicy.processForm(aform)
    aPolicy.createXML(aform)

    # Compute md5 for policy and the create time
    md5 = hashlib.md5()
    md5.update(aPolicy.policy["policy_object"])
    md5sum = md5.hexdigest()
    aPolicy.setmd5(md5sum)
    aPolicy.settime(int(time.time()))

    # Check if the policy exists in the database
    if (policyExists(aPolicy.policy, config)):
        policy_exists = True
    else:
        # Write the policy to a database
        dumpToKVDb(aPolicy.policy, config)

    print ""
    print json.dumps({'policy_exists': policy_exists})

if __name__ == '__main__':
    runStore()