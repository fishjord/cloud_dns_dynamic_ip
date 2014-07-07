#!/usr/bin/env python

import logging
logging.basicConfig()

import os
import sys
import httplib2
import argparse
from oauth2client import tools
from oauth2client.file import Storage
from oauth2client.client import flow_from_clientsecrets
import json
import copy
from apiclient.discovery import build

CLOUD_DNS_SCOPE = 'https://www.googleapis.com/auth/ndev.clouddns.readwrite'


def find_record(records, record_type=None, record_name=None):
    for record in records['rrsets']:
        if ((record_type is None or (record.get('type', '') == record_type)) and (
                record_name is None or (record.get('name', '') == record_name))):
            return record

    return None


def next_soa_record(soa_record):
    assert soa_record['type'] == 'SOA'
    assert len(soa_record['rrdatas']) == 1
    ret = copy.deepcopy(soa_record)

    rrdatas = ret['rrdatas']
    lexemes = rrdatas[0].split()
    lexemes[2] = '{0}'.format(int(lexemes[2]) + 1)
    rrdatas[0] = ' '.join(lexemes)

    return ret


def main():
    parser = argparse.ArgumentParser(parents=[tools.argparser])
    parser.add_argument('--client_secret', help='location of client_secret.json',
                        default='client_secret.json')
    parser.add_argument('--pretend', help='Just pretend, don\'t do anything',
                        default=False, action='store_true')
    parser.add_argument('project_name', help='Google cloud project name')
    parser.add_argument('zone', help='Zone to update')
    parser.add_argument(
        'sub_domain',
        help="Sub domain to map current ip address to")

    flags = parser.parse_args()

    logging.getLogger('oauth2client.util').setLevel(logging.CRITICAL)
    log = logging.getLogger('red.solr.clouddns')

    if flags.logging_level:
      log.setLevel(flags.logging_level)

    if flags.sub_domain == '':
        log.critical(('Very Bad Things(tm) will happen if you '
                           'try to set the root record of your zone '
                           'with this tool'))
        sys.exit(1)

    storage = Storage(os.path.expanduser('~/.cloud_dns_ip_sync_creds'))
    flow = flow_from_clientsecrets(flags.client_secret, scope=CLOUD_DNS_SCOPE)

    credentials = storage.get()

    if credentials is None or credentials.invalid:
        credentials = tools.run_flow(flow, storage, flags)

    http = httplib2.Http()
    auth_http = credentials.authorize(http)

    service = build('dns', 'v1beta1', auth_http)

    records = service.resourceRecordSets().list(
        project=flags.project_name,
        managedZone=flags.zone).execute()

    soa_record = find_record(records, 'SOA')
    fqdn = flags.sub_domain + '.' + soa_record['name']

    old_record = find_record(records, record_name=fqdn)

    body = {
        'additions': [
            next_soa_record(soa_record)],
        'deletions': [soa_record]}

    resp, content = http.request('http://myexternalip.com/raw')
    current_ip = content.strip()

    new_record = {
        'kind': 'dns%resourceRecordSet',
        'type': 'A',
        'rrdatas': [current_ip],
        'ttl': '21600',
        'name': fqdn}

    body['additions'].append(new_record)
    if old_record:
        assert old_record.get('rrdatas', False)
        assert len(old_record['rrdatas']) == 1 
        if old_record['rrdatas'][0] == current_ip and not flags.pretend:
            log.debug('IP address unchanged, exiting')
            sys.exit(0)

        body['deletions'].append(old_record)

    log.info(json.dumps(body, indent=1))
    if not flags.pretend:
        response = service.changes().create(
            project=flags.project_name,
            managedZone=flags.zone,
            body=body).execute()
        log.info(response)

if __name__ == '__main__':
    main()
