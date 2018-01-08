#!/usr/bin/python3
import os
import sys
import subprocess
import logging
import argparse
from jinja2 import Environment, FileSystemLoader

#-----------------------------------------------------------------------------
# Examples
# Add: python traveltoolssl.py -a add -d test.prueba.es --agencyid 1 --application www.traveltool.es --forcessl 1
# Delete: python traveltoolssl.py -a delete -d test.prueba.es
# Change: python traveltoolssl.py -a change -d test.prueba.com --agencyid 2 --application www.traveltool.es
# Addagent: python traveltoolssl.py -a addagent -d test.prueba.com --agentname virgilio --agenturl /mshomett/home?agente=5880
# Delagent: python traveltoolssl.py -a delagent -d test.prueba.com --agentname virgilio
# #-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
# Globals
#-----------------------------------------------------------------------------
#CERT_FOLDER = 'c:/temp'
#NGINX_SITES = 'c:/temp'
CERT_FOLDER = '/etc/letsencrypt/live'
NGINX_SITES = '/etc/nginx/sites-enabled'
THIS_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_WEBSITE = 'traveltool_website.j2'
TEMPLATE_SSL_WEBSITE = 'traveltool_ssl_website.j2'
TEMPLATE_AGENT = 'agent.j2'
TEMPLATE_ENVIRONMENT = Environment(
    autoescape=False,
    loader=FileSystemLoader(os.path.join(THIS_DIR)),
    trim_blocks=False)
TRAVELTOOL_WILDCARD = 'wildcard.traveltool.es'

#-----------------------------------------------------------------------------
# Functions
#-----------------------------------------------------------------------------

def parse_args():
    logger.info("Parsing command arguments...")

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "-a",
        "--action",
        type = str,
        required=True,
        help = "Specify an action: add, delete, change, addagent, delagent")
 
    parser.add_argument(
        "-d",
        "--domain",
        type = str,
        required=True,
        help = "Specify the domain")

    parser.add_argument(
        "--agencyid",
        default = None,
        type = int,
        nargs='?',
        help = "Specify the agency id")
 
    parser.add_argument(
        "--application",
        default = None,
        type = str,
        nargs='?',
        help = "Specify the application (e.g.: www.traveltool.es, www.traveltool.pt, etc)")

    parser.add_argument(
        "--newdomain",
        default = None,
        type = str,
        nargs='?',
        help = "Specify the domain")

    parser.add_argument(
        "--agentname",
        default = None,
        type = str,
        nargs='?',
        help = "Specify the agent name")

    parser.add_argument(
        "--agenturl",
        default = None,
        type = str,
        nargs='?',
        help = "Specify the agent url")

    parser.add_argument(
        "--forcessl",
        default = 0,
        type = int,
        nargs='?',
        help = "Specify is force redirection to ssl (default: 0)")
    options = parser.parse_args()
    logger.info("Parsed command arguments")
    return options

def exec_command(cmd):
    logger.info("Executing: %s", cmd)
    child = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True)
    streamdata = (child.communicate()[0]).decode(sys.stdout.encoding)
    logger.info("Execution finished")
    logger.debug("Result: %s", str(streamdata))
    return child.returncode, streamdata

def template_website(template, tmpdomain, tmpagencyId, tmpapplication, tmpcertificate):
    logger.info("Starting website template")

    templateWebsite = os.path.join(THIS_DIR, template)
    if not os.path.exists(templateWebsite):
        logger.critical("Couldn't find template file %s", templateWebsite)
        sys.exit(1)

    renderSite=TEMPLATE_ENVIRONMENT.get_template(template).render(domain = tmpdomain, agency = tmpagencyId, application = tmpapplication, certificate = tmpcertificate)
    logger.debug("Output template render: %s", renderSite)

    if not os.path.exists(NGINX_SITES):
        logger.critical("Couldn't find Nginx sites folder %s", NGINX_SITES)
        sys.exit(1)
    domainSite = os.path.join(NGINX_SITES, tmpdomain + ".conf")
    try:
        with open(domainSite, 'w') as f:
            f.write(renderSite)
    except:
        logger.critical("Unexpected error creating website file:", sys.exc_info()[0])
        sys.exit(1)
    logger.debug("Site templated in %s", tmpdomain)
    
    logger.info("Finished website template")
    return

def checkparamaters(arguments):
    logger.info("Checking input parameters...")

    action = arguments.action.lower()
    domain = arguments.domain.lower()
    agencyId = arguments.agencyid
    application = arguments.application
    agentName = arguments.agentname
    agentUrl = arguments.agenturl
    forcessl = arguments.forcessl

    if action == "add":
        logger.debug("check paramater for add domain")
        if not (action and domain and agencyId and application):
            logger.critical("Invalid parameters for action %s. Required arguments: action, domain, agencyid, application", action)
            sys.exit(1)
    elif action == "delete":
        if not (action and domain):
            logger.critical("Invalid parameters for action %s. Required arguments: action, domain", action)
            sys.exit(1)
    elif action == "change":
        if not (action and domain and agencyId and application):
            logger.critical("Invalid parameters for action %s. Required arguments: action, domain, agencyid, application", action)
            sys.exit(1)
    elif action == "addagent":
        if not (action and domain and agentName and agentUrl):
            logger.critical("Invalid parameters for action %s. Required arguments: action, domain, agentname, agenturl", action)
            sys.exit(1)
    elif action == "delagent":
        if not (action and domain and agentName):
            logger.critical("Invalid parameters for action %s. Required arguments: action, domain, agentname", action)
            sys.exit(1)
    else:
        logger.critical("action %s no allowed", action)
        sys.exit(1)

    logger.info("Checked input parameters")

    return action, domain, agencyId, application, agentName, agentUrl, forcessl

def createdomain(domain, agencyId, application, forcessl):
    logger.info("Creating new domain %s", domain)

    #If traveltool domain, skip certification request (use wildcard)
    if ".traveltool." not in domain:
        #Check if certificate folder exists
        if not os.path.exists(CERT_FOLDER):
            logger.critical("Couldn't find certificate folder %s", CERT_FOLDER)
            sys.exit(1)

        #Check if certificate exists
        certDomain = os.path.join(CERT_FOLDER, domain + "/cert.pem")
        if not os.path.exists(certDomain):
            logger.info("Couldn't find certificate for domain %s", certDomain)

            #Execute certbot and check if certificate exists
            resultCode, resultOutput = exec_command(['certbot','certificates'])
            logger.debug("Output: %s", resultOutput)
            if not (resultCode == 0):
                logger.critical("Error executing certbot: %s", resultOutput)
                sys.exit(1)
        certificate = domain
    else:
        certificate = TRAVELTOOL_WILDCARD

    #Template nginx site
    if forcessl == 0:
        template = TEMPLATE_WEBSITE
        template_website(template, domain, agencyId, application, certificate)
    else:
        template = TEMPLATE_SSL_WEBSITE
        template_website(template, domain, agencyId, application, certificate)

    #Check nginx config and reload

    logger.info("Created new domain %s", domain)

    return

def deletedomain(domain):
    logger.info("Deleting website for domain %s ...", domain)

    siteFile = os.path.join(NGINX_SITES, domain + ".conf")
    if os.path.exists(siteFile):
        try:
            os.remove(siteFile)
        except:
            logger.critical("Unexpected error deleting website file", sys.exc_info()[0])
            sys.exit(1)
    else:
        logger.warning("Site file doesn't exist: %s",siteFile)

    logger.info("Deleted website for domain %s",domain)

    return

def changedomain(domain, agencyId, application, forcessl):
    logger.info("Changing website configuration for domain %s ...", domain)

    deletedomain(domain)
    createdomain(domain,agencyId,application,forcessl)

    logger.info("Changed website configuration for domain %s", domain)

    return

def addagent(domain, agentName, agentUrl):
    logger.info("Creating new agent %s ...", agentName)

    #Check if domain file exist
    siteFile = os.path.join(NGINX_SITES, domain + ".conf")
    if not os.path.exists(siteFile):
        logger.critical("Couldn't find site file for domain %s", domain)
        sys.exit(1)

    #Template agent file
    templateAgent = os.path.join(THIS_DIR, TEMPLATE_AGENT)
    if not os.path.exists(templateAgent):
        logger.critical("Couldn't find template file %s", templateAgent)
        sys.exit(1)
    renderAgent = TEMPLATE_ENVIRONMENT.get_template(TEMPLATE_AGENT).render(name = agentName, url = agentUrl)

    #Create agent File
    agentDomainFolder =  os.path.join(NGINX_SITES, domain + ".d/") 
    if not os.path.exists(agentDomainFolder):
        logger.warning("Couldn't find agent folder for domain %s", agentDomainFolder)
        try: 
            os.makedirs(agentDomainFolder)
        except: 
            logger.critical("Unexpected error creating agent folder:", sys.exc_info()[0])
            sys.exit(1)
    agentFile =  os.path.join(NGINX_SITES, domain + ".d/", agentName + ".conf")
    try:
        logger.info("Creating file for agent: %s", agentFile)
        with open(agentFile, 'w') as f:
            f.write(renderAgent)
    except:
        logger.critical("Unexpected error creating agent file:", sys.exc_info()[0])
        sys.exit(1)

    logger.info("Created new agent %s", agentName)

    return

def delagent(domain, agentName):
    logger.info("Starting to delete agent: %s ...", agentName)

    agentFile =  os.path.join(NGINX_SITES, domain + ".d/", agentName + ".conf")
    try:
        os.remove(agentFile)
    except:
        logger.critical("Unexpected error deleting agent file:", sys.exc_info()[0])
        sys.exit(1)

    logger.info("Finished to delete agent: %s", agentName)

    return

def main():
    #Start script
    logger.info("Start script")

    #Args
    readArgs = parse_args()
    logger.info("Arguments: %s ", readArgs)

    #Check arguments
    action, domain, agencyId, application, agentName, agentUrl, forcessl = checkparamaters(readArgs)

    ### COMMAND ###
    if action == "add":
        logger.debug("create domain")
        createdomain(domain,agencyId,application,forcessl)
    elif action == "delete":
        logger.debug("delete domain")
        deletedomain(domain)
    elif action == "change":
        logger.debug("change domain")
        changedomain(domain,agencyId,application,forcessl)
    elif action == "addagent":
        logger.debug("add agent")
        addagent(domain, agentName, agentUrl)
    elif action == "delagent":
        logger.debug("delete agent")
        delagent(domain, agentName)
    else:
        logger.critical("action %s no allowed", action)
        sys.exit(1)

    ### CHECK NGINX AND RELOAD

    #End script
    logger.info("End script")



### MAIN ###
if __name__ == '__main__':
    #log config
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    # create console handler and set level to debug
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    # create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(funcName)s - %(levelname)s - %(message)s')
    # add formatter to ch
    ch.setFormatter(formatter)
    # add ch to logger
    logger.addHandler(ch)
    main()