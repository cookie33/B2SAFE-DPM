#!/usr/bin/env python

__author__ = 'Claudio Cacciari, Cineca, c.cacciari@cineca.it'

import json
import time
import logging
import requests
import datetime
import xmltodict
import hashlib
from lxml import etree
from ConfigLoader import ConfigLoader

# This class represent the DPM database.
# Its functions perform read/write operations on the DB.
# Transforming the results to/from XML format.

class ServerConnector:

    def __init__(self, config, test=False, logName=None, debug=False):
        """ Initialize the ServerConnector class

        @type  config:  string
        @param config:  The configuration file path
        @type  test:    boolean    
        @param test:    If True, the code is executed without performing real 
                        operations
        @type  logName: string
        @param logName: The name of the parent logger
        @type  debug:   boolean
        @param debug:   If True the debug is enabled
        """
        # Namespaces constants, they could be moved to a centralized place"
        self.polNs = 'http://eudat.eu/2013/policy'
        self.irodsNs='http://eudat.eu/2013/iRODS-policy'
        self.staNs = 'http://eudat.eu/2016/policy-status'

        # logging initialization
        if logName: loggerName = logName + ".ServerConnector"
        else: logName = "ServerConnector"
        self.logger = logging.getLogger(loggerName)

        if debug:
            self.logger.setLevel(logging.DEBUG)
        else:
            self.logger.setLevel(logging.INFO)

        self.test = test
        self.debug = debug

        # load properties from configuration
        self.config = ConfigLoader(config)

        # load credentials
        self.auth = None
        with open(self.config.SectionMap('DpmServer')['tokenfile'], 'r') as fin:
            token_map = json.loads(fin.read())
            fin.close()
            username = token_map['token']
            password = token_map['pword']
            self.auth = (username, password)

        # this is the parameter to manage the SSL public key based encryption.
        # Look at the python module "requests" api for details.
        http_verify = self.config.SectionMap('DpmServer')['http_verify']
        self.veri = True
        if http_verify == "False":
            self.veri = False
        elif http_verify != "True":
            self.veri = http_verify
       
        # definition of the DB URL
        self.url = '%s://%s:%s%s' % (
                                self.config.SectionMap('DpmServer')['scheme'],
                                self.config.SectionMap('DpmServer')['hostname'],
                                self.config.SectionMap('DpmServer')['port'],
                                self.config.SectionMap('DpmServer')['path'])

#TODO verify if it is possible to merge update and create in a single function

    def updateStatus(self, policyId, state):
        """ This method updates or creates, if not already present, the status 
            document related to a specific policy document.

        @type  policyId: string
        @param policyId: The policy id
        @type  state:    string
        @param state:    The status value [QUEUED | FAILED | DONE | RUNNING]
        @rtype:          string
        @return:         The response of the HTTP POST request to the DB
        """
        # check if the status doc is already available, 
        # if not it creates a new one
        if not self.getStatus(policyId)[1]:
            return self.createStatus(policyId, state)

        statusdb = self.config.SectionMap('DpmServer')['statusdbname']

        # get the current UNIX timestamp and convert to 2016-08-21T09:30:10Z
        timestamp = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())

        # xquery request to update the status doc fields: status and timestamp
        post_data = '''<rest:query xmlns:rest="http://basex.org/rest">
                         <rest:text>
                           declare namespace tns = "{}";
                           for $res in collection("{}")/tns:policy
                             where $res[@uniqueid = "{}"]
                             return(
                             replace value of node $res/tns:status with '{}',
                             replace value of node $res/tns:timestamp with '{}'
                             )
                      </rest:text>
                    </rest:query>'''.format(self.staNs, statusdb, policyId, 
                                            state, timestamp)

        self.logger.info('Updating policies [{}]'.format(self.url))
        self.logger.debug('post_data: ' + post_data + '; auth: ' +
                          str(self.auth) + '; http verify: ' + str(self.veri))

        # perform the HTTP POST request to the DB
        response = requests.post(self.url, data=post_data,
                                 auth=self.auth, verify=self.veri)

        if response is not None and len(response.text) > 0:
            self.logger.debug("response is: " + response.text)
        
        return response


    def createStatus(self, policyId, state):
        """ This method create a new status document related to a specific policy 

        @type  policyId: string
        @param policyId: The policy id
        @type  state:    string
        @param state:    The status value [QUEUED | FAILED | DONE | RUNNING]
        @rtype:          boolean
        @return:         True if the document is created, False otherwise
         
        """
        self.logger.info('Creating a new policy status document with id: ' + 
                          policyId)

        # check if a policy doc with the given id is available
        policyDict, policyDoc = self.getPolicy(policyId)
        if policyDoc is None:
            self.logger.debug("No policy with id [{}] found".format(policyId))
            return policyDoc

        # create the XML status doc
        name = policyDict[self.polNs+':policy']['@name']
        ver = policyDict[self.polNs+':policy']['@version']
        chk_alg = 'MD5'
        chk_val = hashlib.md5(policyDoc.encode()).hexdigest()
        status = state
        timestamp = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
        
        statusDoc = '''<?xml version="1.0" encoding="UTF-8"?>
                    <ns0:policy uniqueid="{}" xmlns:ns0="{}">
                       <ns0:name>{}</ns0:name>
                       <ns0:version>{}</ns0:version>
                       <ns0:checksum method="{}">{}</ns0:checksum>
                       <ns0:status>{}</ns0:status>
                       <ns0:timestamp>{}</ns0:timestamp>
                    </ns0:policy>'''.format(policyId, self.staNs, name, ver,
                                            chk_alg, chk_val, status, timestamp)

        # validate the the created status doc: 
        # if it is not valid do not perform any change to the DB
        if not self.validateXML(statusDoc):
            return False

        # perform the HTTP PUT request to the DB
        statusdb = self.config.SectionMap('DpmServer')['statusdbname']
        put_url = '{}/{}/{}-{}_status.xml'.format(self.url, statusdb, name, ver)
        headers = {'Content-Type': 'application/xml'}
        self.logger.debug('put_url: ' + put_url + '; put_data: ' + statusDoc
                          + '; auth: ' + str(self.auth) + '; http verify: ' 
                          + str(self.veri))
        response = requests.put(put_url, data=statusDoc, headers=headers,
                                auth=self.auth, verify=self.veri)

        self.logger.debug("response is: " + response.text)
        return True


    def listPolicies(self, attributes=None, start_date=0, end_date=2544652800):
        """ This method lists the policies which satisfied input requirements 
        @type  attributes: dictionary
        @param attributes: The list of key-value pairs to filter the policies
        @type  start_date: string
        @param start_date: The start date, as unix timestamp, of the range 
                           considered to search for policies (default=None)
        @type  end_date:   string
        @param end_date:   The end date, as unix timestamp, of the range 
                           considered to search for policies (default=2050/08)
        @rtype:          list of strings
        @return:         A list of urls, pointing to the policies in the DB
        """
        policiesdb = self.config.SectionMap('DpmServer')['policiesdbname']

        # xquery filter condition clause built from the attributes dictionary
        data_filter = ''
        if attributes:
            for key in attributes.keys():
                if key.startswith('source') or key.startswith('target'):
                    pair = key.split('.')
                    if len(pair) != 2:
                        return None
                    if pair[1] == 'site':
                        data_filter += (' and $policy//tns:{}/tns:location/'
                                       +'irodsns:site[matches(text(), "{}")]'
                                       ).format(pair[0], attributes[key])
                    elif pair[1] == 'pid':
                        data_filter += (' and $policy//tns:{}/'
                                       +'tns:persistentIdentifier'
                                       +'[starts-with(text(), "{}")]'
                                       ).format(pair[0], attributes[key])
                    continue
                if key == 'action':
                    data_filter += (' and $policy//tns:action/tns:type[matches('
                                   +'text(), "{}")]'.format(attributes[key]))
                    continue
                data_filter += ' and $policy[matches(@{},"{}")]'.format(key, 
                                                                 attributes[key])
        # xquery request to select policy docs from the DB according to the
        # requirements provided as input
        post_data = '''<rest:query xmlns:rest="http://basex.org/rest">
                          <rest:text>
                             declare namespace tns = "%s";
                             declare namespace irodsns = "%s";
                             let $results := collection("%s")/tns:policy
                             for $policy in $results where $policy
                                 %s
                                 and $policy[@created > %s]
                                 and not($policy[@created > %s])
                                     let $policies := string-join(("%s/%s", 
                                                         db:path($policy)), "/")
                             return $policies 
                          </rest:text>
                     </rest:query>''' % (self.polNs, self.irodsNs, policiesdb, 
                                         data_filter, start_date, end_date, 
                                         self.url, policiesdb)

        self.logger.info('Listing policies [%s]' % self.url)
        self.logger.debug('post_data: ' + post_data + '; auth: ' + 
                          str(self.auth) + '; http verify: ' + str(self.veri))
 
        # perform the HTTP POST request to the DB
        response = requests.post(self.url, data=post_data, 
                                 auth=self.auth, verify=self.veri)
        self.logger.debug("response is: " + response.text)

        # response is split because a list of policies is returned
        policy_urls = response.text.strip().split("\n")
        if (policy_urls is None or len(policy_urls) == 0 
            or (len(policy_urls) == 1 and len(policy_urls[0]) == 0)):
            self.logger.info('No response found')
            return None
        else:
            self.logger.info('Found %d policies' % (len(policy_urls)))
            return policy_urls


    def getDocumentByUrl(self, url, query=None):
        """ Get a document from the DB based on its url 

        @type  url:   string
        @param url:   The document url
        @type  query: string 
        @param query: An xpath query (default=None)
        @rtype:       string
        @return:      The document if found, None otherwise. 
                      If a query is specified an XML snippet could be returned
        """
        self.logger.info('Getting xml doc from url ' + url)
        #expected xquery format like "//*:policy/@uniqueid/data()"
        if query:
            url = url + '?query=' + query
            self.logger.debug('Performing query: ' + query)

        # perform the HTTP GET request to the DB
        response = requests.get(url, auth=self.auth, verify=self.veri)
        if response is None:
            self.logger.info('No response found')
            return response
        else:
            self.logger.info('Document found')
            self.logger.debug('response: ' + response.text)
            return response.text


    def getStatus(self, policyId):
        """ Get a status document from the DB based on its id 

        @type  policyId: string
        @param policyId: The policy id
        @rtype:          tuple(dictionary, string)
        @return:         A tuple of two representations of the same document
        """
 
        statusdb = self.config.SectionMap('DpmServer')['statusdbname']
        doc = self.getDocumentById(policyId, statusdb, self.staNs)
        if doc is not None:
            # it use the "xmltodict" module to transform the XML doc to a python
            # dictionary, taking into account the namespaces
            return (xmltodict.parse(doc, process_namespaces=True), doc)
        return (None, doc)


    def getPolicy(self, policyId):
        """ Get a policy document from the DB based on its id 
        
        @type  policyId: string
        @param policyId: The policy id
        @rtype:          tuple(dictionary, string)
        @return:         A tuple of two representations of the same document
        """
        statusdb = self.config.SectionMap('DpmServer')['policiesdbname']
        doc = self.getDocumentById(policyId, statusdb, self.polNs)
        if doc is not None:
            # it uses the "xmltodict" module to transform the XML doc to a python
            # dictionary, taking into account the namespaces
            return (xmltodict.parse(doc, process_namespaces=True), doc)
        return (None, doc)


    def getDocumentById(self, policyId, dbname, ns):
        """ Get a document from the DB based on its id 

        @type  policyId: string
        @param policyId: The policy id
        @type  dbname:   string
        @param dbname:   The name of the BaseX DB to query
        @type  ns:       string
        @param ns:       The namespace related to the wanted document
        @rtype:          string
        @return:         The document if found, None otherwise
        """
        self.logger.info('Getting xml doc with id: ' + policyId)

        # xquery request to select a single document based on the id
        post_data = '''<rest:query xmlns:rest="http://basex.org/rest">
                         <rest:text>
                           declare namespace tns = "{}";
                           for $res in collection("{}")/tns:policy
                               where $res[@uniqueid = "{}"]
                               return $res
                      </rest:text>
                    </rest:query>'''.format(ns, dbname, policyId)

        self.logger.debug('post_data: ' + post_data + '; auth: ' +
                          str(self.auth) + '; http verify: ' + str(self.veri))

        # perform the HTTP POST request to the DB
        response = requests.post(self.url, data=post_data,
                                 auth=self.auth, verify=self.veri)
        if response is None or len(response.text) == 0:
            self.logger.info('No response found')
            return None
        else:
            self.logger.info('Document found')
            self.logger.debug('response: [{}]'.format(response.text))
            return response.text


    def validateXML(self, xmlText):
        """ Validate the XML formatted text passed as input 

        @type  xmlText: string 
        @param xmlText: the input XML doc
        @rtype:         boolean
        @return:        True if the doc is valid, False otherwise
        """
        self.logger.info('Validating the xml')
        # get the schema local file path from the configuration file
        schemaPath = self.config.SectionMap('Schemas')['status']
        # load the schema doc 
        xmlSchemaDoc = etree.parse(schemaPath)
        xmlschema = etree.XMLSchema(xmlSchemaDoc)
        # parse the XML input
        root = etree.fromstring(xmlText)
        # validate the XML doc
        if not xmlschema(root):
            self.logger.error(xmlschema.error_log.last_error)
            return False
        self.logger.debug('The xml is valid')
        return True
