#!/usr/bin/env python
import sys
import os
import ConfigParser
import sqlite3
import json
import smtplib

def sendEmail(config, dataVals):
    '''Function to construct and send the email to the user
    '''
    sender = "noreply@usit.uio.no"
    receivers = [dataVals["email"]]
    msg = file(config.get("EMAIL", "header"), 'r').read() 
    msg = msg % (dataVals["email"], dataVals["e_subject"])
    msg = msg + dataVals["e_body"]

    try:
        smtpObj = smtplib.SMTP("localhost")
        smtpObj.sendmail(sender, receivers, msg)
        print msg
    except smtplib.SMTPException:
        print "Error: unable to send email"

def update(config):
    '''Function to update the database and email the user
    '''
    print 'Content-Type: application/json charset=utf-8'
    print ''

    dataVals = json.load(sys.stdin)
    status_id = -1

    conn = sqlite3.connect(config.get("DATABASE", "profile_name"))
    cur = conn.cursor()

    # Get the status id according to the approval type
    if (dataVals["approval"] == "approve"):
        cur.execute('''select status_id from status where 
                status = 'approved' ''')
        status_id = int(cur.fetchone()[0])
    elif (dataVals["approval"] == "reject"):
        cur.execute('''select status_id from status where
                status = 'declined' ''')
        status_id = int(cur.fetchone()[0])

    if (status_id >= 0):
        cur.execute('''update user_community set status_id=? where
                user_comm_id=?''', (status_id, dataVals["uid"]))
        conn.commit()
        sendEmail(config, dataVals)


if __name__ == '__main__':
    cfgfile = './config/policy_schema.cfg'
    config = ConfigParser.ConfigParser()
    config.read(cfgfile)
    update(config)