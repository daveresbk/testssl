from flask import Flask, url_for, request, make_response, Response, render_template, abort, jsonify, flash
import logging
import os
from logging.handlers import RotatingFileHandler
from jinja2 import Environment, FileSystemLoader
app = Flask(__name__)

#-----------------------------------------------------------------------------
###Setup###
# flask
#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
# Examples
# Add: python traveltoolssl.py -a add -d test.prueba.es --agencyid 1 --application www.traveltool.es --forcessl 1
# Delete: /configuration?command=delete&domain=test1.prueba.com
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
CERTBOT_CREATECERT = "certbot certonly --webroot -w /var/www/html/ -d %s --agree-tos --no-eff-email  --no-redirect --keep --register-unsafely-without-email"
CERTBOT_DELETECERT = "certbot delete --cert-name %s"
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

def abortbyerror(text):
    app.logger.critical(text)
    flash(text,'error')
    abort(500)

def exec_command(cmd):
    #logger.info("Executing: %s", cmd)
    child = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True)
    streamdata = (child.communicate()[0]).decode(sys.stdout.encoding)
    #logger.info("Execution finished")
    #logger.debug("Result: %s", str(streamdata))
    return child.returncode, streamdata

def template_website(template, tmpdomain, tmpagencyId, tmpapplication, tmpcertificate):
    #logger.info("Starting website template")

    templateWebsite = os.path.join(THIS_DIR, template)
    if not os.path.exists(templateWebsite):
        message="Couldn't find template file %s" % templateWebsite
        abortbyerror(message)

    renderSite=TEMPLATE_ENVIRONMENT.get_template(template).render(domain = tmpdomain, agency = tmpagencyId, application = tmpapplication, certificate = tmpcertificate)
    #logger.debug("Output template render: %s", renderSite)

    if not os.path.exists(NGINX_SITES):
        message="Couldn't find Nginx sites folder %s" % NGINX_SITES
        abortbyerror(message)
    
    domainSite = os.path.join(NGINX_SITES, tmpdomain + ".conf")
    try:
        with open(domainSite, 'w') as f:
            f.write(renderSite)
    except:
        message="Unexpected error creating website file. Error: " + sys.exc_info()[0]
        abortbyerror(message)
    #logger.debug("Site templated in %s", tmpdomain)
    
    #logger.info("Finished website template")
    return

def checkparameters(argumentos):
    app.logger.info("Checking input parameters...")

    action=''
    domain=''
    agencyId=''
    application=''
    agentName=''
    agentUrl=''
    newdomain=''
    forcessl=''
    showlogs=''
    if 'command' in argumentos:
        action=argumentos['command']
    if 'domain' in argumentos:
        domain=argumentos['domain']
    if 'idagencia' in argumentos:
        agencyId=argumentos['idagencia']
    if 'application' in argumentos:
        application=argumentos['application']
    if 'name' in argumentos:
        agentName=argumentos['name']
    if 'url' in argumentos:
        agentUrl=argumentos['url']
    if 'newdomain' in argumentos:
        newdomain=argumentos['newdomain']
    if 'forcessl' in argumentos: 
        forcessl=argumentos['forcessl']
    if 'showlogs' in argumentos: 
        showlogs=argumentos['showlogs']

    if action == "add":
        if not (action and domain and agencyId and application):
            message="Invalid parameters for action %s. Required arguments: command, domain, idagencia, application" % action
            abortbyerror(message)
    elif action == "delete":
        if not (action and domain):
            message="Invalid parameters for action %s. Required arguments: command, domain" % action
            abortbyerror(message)
    elif action == "change":
        if not (action and domain and agencyId and application):
            message="Invalid parameters for action %s. Required arguments: command, domain, idagencia, application" % action
            abortbyerror(message)
    elif action == "addagent":
        if not (action and domain and agentName and agentUrl):
            message="Invalid parameters for action %s. Required arguments: command, domain, name, url" % action
            abortbyerror(message)
    elif action == "delagent":
        if not (action and domain and agentName):
            message="Invalid parameters for action %s. Required arguments: command, domain, name" % action
            abortbyerror(message)
    else:
        message="action %s no allowed" % action
        abortbyerror(message)

    app.logger.info("Checked input parameters")

    return action, domain, agencyId, application, agentName, agentUrl, forcessl, showlogs

def createdomain(domain, agencyId, application, forcessl):
    #logger.info("Creating new domain %s", domain)

    #If traveltool domain, skip certification request (use wildcard)
    if ".traveltool." not in domain:
        #Check if certificate folder exists
        if not os.path.exists(CERT_FOLDER):
            message="Couldn't find certificate folder %s" % CERT_FOLDER
            abortbyerror(message)

        #Check if certificate exists
        certDomain = os.path.join(CERT_FOLDER, domain + "/cert.pem")
        if not os.path.exists(certDomain):
            #logger.info("Couldn't find certificate for domain %s", certDomain)

            #Execute certbot and check if certificate exists
            strCmd = CERTBOT_CREATECERT % (domain)
            resultCode, resultOutput = exec_command(strCmd)
            if not (resultCode == 0):
                message="Error executing certbot request for domain: %s" % resultOutput
                abortbyerror(message)
        #logger.info (resultOutput)
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

    #logger.info("Created new domain %s", domain)

    return

def deletedomain(action,domain):
    #logger.info("Deleting domain %s ...", domain)

    #delete website config
    siteFile = os.path.join(NGINX_SITES, domain + ".conf")
    if os.path.exists(siteFile):
        try:
            os.remove(siteFile)
            #logger.info("Deleted website for domain %s",domain)
        except:
            message="Unexpected error deleting website file. Error: " & sys.exc_info()[0]
            abortbyerror(message)
    else:
        #logger.warning("Site file doesn't exist: %s",siteFile)

    #only if action delete, if action change not delete certificate
    if action == "delete":   
        if ".traveltool." not in domain:
            #Check if certificate exists
            certDomain = os.path.join(CERT_FOLDER, domain)
            if not os.path.exists(certDomain):
                #logger.warning("Couldn't find certificate for domain %s", certDomain)
            else:
                strCmd = CERTBOT_DELETECERT % (domain)
                resultCode, resultOutput = exec_command(strCmd)
                if not (resultCode == 0):
                    #logger.warning("Error executing certbot delete for domain: %s", resultOutput)
                try:
                    os.remove(certDomain)
                    #logger.info("Deleted certificate folder for domain %s",domain)
                except:
                    message="Unexpected error deleting certificate folder. Error: " % sys.exc_info()[0]
                    abortbyerror(message)

    #logger.info("Deleted domain %s",domain)

    return

def changedomain(domain, agencyId, application, forcessl):
    #logger.info("Changing website configuration for domain %s ...", domain)

    deletedomain("change",domain)
    createdomain(domain,agencyId,application,forcessl)

    #logger.info("Changed website configuration for domain %s", domain)

    return

def addagent(domain, agentName, agentUrl):
    #logger.info("Creating new agent %s ...", agentName)

    #Check if domain file exist
    siteFile = os.path.join(NGINX_SITES, domain + ".conf")
    if not os.path.exists(siteFile):
        message="Couldn't find site file for domain %s" % domain
        abortbyerror(message)

    #Template agent file
    templateAgent = os.path.join(THIS_DIR, TEMPLATE_AGENT)
    if not os.path.exists(templateAgent):
        message="Couldn't find template file %s" % templateAgent
        abortbyerror(message)
    renderAgent = TEMPLATE_ENVIRONMENT.get_template(TEMPLATE_AGENT).render(name = agentName, url = agentUrl)

    #Create agent File
    agentDomainFolder =  os.path.join(NGINX_SITES, domain + ".d/") 
    if not os.path.exists(agentDomainFolder):
        #logger.warning("Couldn't find agent folder for domain %s", agentDomainFolder)
        try: 
            os.makedirs(agentDomainFolder)
        except: 
            message="Unexpected error creating agent folder. Error: " % sys.exc_info()[0]
            abortbyerror(message)
    agentFile =  os.path.join(NGINX_SITES, domain + ".d/", agentName + ".conf")
    try:
        #logger.info("Creating file for agent: %s", agentFile)
        with open(agentFile, 'w') as f:
            f.write(renderAgent)
    except:
        message="Unexpected error creating agent file. Error: " % sys.exc_info()[0]
        abortbyerror(message)

    #logger.info("Created new agent %s", agentName)

    return

def delagent(domain, agentName):
    #logger.info("Starting to delete agent: %s ...", agentName)

    agentFile =  os.path.join(NGINX_SITES, domain + ".d/", agentName + ".conf")
    try:
        os.remove(agentFile)
    except:
        message="Unexpected error deleting agent file. Error: " + sys.exc_info()[0]
        abortbyerror(message)

    #logger.info("Finished to delete agent: %s", agentName)

    return



 ### ROUTES ###
@app.errorhandler(404)
def page_not_found(e):
    return render_template('400.html'), 404

@app.errorhandler(500)
def custom500(error):
    return render_template('500.html'),500
#    response = jsonify({'message': error.description})
#    return response, 500

@app.route('/', methods = ['GET'])
def web_root():
    return 'OK'
#    resp = make_response(render_template('error.html'), 404)
#    resp.headers['X-Reason'] = 'Page not found'
#    return resp

@app.route('/configuration', methods = ['GET'])
def configuration():
    action, domain, agencyId, application, agentName, agentUrl, forcessl, showlogs=checkparameters(request.args)

    ### COMMAND ###
    if action == "add":
        #logger.debug("create domain")
        createdomain(domain,agencyId,application,forcessl)
    elif action == "delete":
        #logger.debug("delete domain")
        deletedomain(action,domain)
    elif action == "change":
        #logger.debug("change domain")
        changedomain(domain,agencyId,application,forcessl)
    elif action == "addagent":
        #logger.debug("add agent")
        addagent(domain, agentName, agentUrl)
    elif action == "delagent":
        #logger.debug("delete agent")
        delagent(domain, agentName)
    else:
        message="Action %s no allowed" % action
        abortbyerror(message)

    ### TODO: CHECK NGINX AND RELOAD

    return render_template('response.html',showlogs=showlogs),200

### MAIN ###
if __name__ == '__main__':
    logHandler = RotatingFileHandler('info.log', maxBytes=1000, backupCount=1)
    # set the log handler level
    logHandler.setLevel(logging.INFO)
    # set the app logger level
    app.logger.setLevel(logging.INFO)
    app.logger.addHandler(logHandler)    
    app.secret_key = 'traveltool'
    app.run()