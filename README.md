# Overview
The script [update_dynamic_ip.py] is designed to manage syncing the external ip address (that is, the ip address the world sees, as viewed from myexternalip.com) of the machine the script is run on with a google cloud dns managed zone.

# Requirements
* google-api-python-client
* Google Cloud Platform Project (with [CloudDNS](https://developers.google.com/cloud-dns/getting-started) enabled)
* Valid client secrets json file ([instructions](https://developers.google.com/api-client-library/python/guide/aaa_oauth#acquiring))

# Getting Started

* Run the script once to setup OAuth permissions
* Schedule the script to run (cron)

# Usage
usage: update_dynamic_ip.py project_name zone sub_domain 

# Program Flow
* List all records in the managed zone
  * Check that there is an SOA record
  * Check if there is an existing sub-domain record
* Query for external ip address from myexternalip.com
* Check to see if our ip has changed
* Create a new SOA record (with increased serial number)
* Create new A record for the given subdomain
* Send change request
