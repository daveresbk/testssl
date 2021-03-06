from flask import Flask, url_for, request, make_response, Response, render_template, abort, jsonify, flash
import logging
import os
import sys
import subprocess
import re
from time import strftime
from logging.handlers import RotatingFileHandler
from jinja2 import Environment, FileSystemLoader
import http.client
import socket

app = Flask(__name__)
logHandler = RotatingFileHandler('info.log', maxBytes=1000, backupCount=10)
# set the log handler level
logHandler.setLevel(logging.INFO)
# set the app logger level
app.logger.setLevel(logging.INFO)
app.logger.addHandler(logHandler)
app.secret_key = 'traveltool'

#-----------------------------------------------------------------------------
###Setup###
# flask
#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
# Examples
# Add TRV: /configuration?command=add&domain=test1.traveltool.tech&idagencia=66&application=www.traveltool.es
# Add NO TRV: /configuration?command=add&domain=test1.toolfactory.tech&idagencia=66&application=www.traveltool.es
# Delete: /configuration?command=delete&domain=test1.prueba.com
# Change: /configuration?command=change&domain=test1.toolfactory.tech&idagencia=99&application=www.traveltool.es
# Addagent: /configuration?command=addagent&domain=test1.toolfactory.tech&name=david&url=/homett
# Delagent: /configuration?command=delagent&domain=test1.toolfactory.tech&name=david
# #-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
# Globals
#-----------------------------------------------------------------------------
#CERT_FOLDER = 'c:/temp'
#NGINX_SITES = 'c:/temp'
CERT_FOLDER = '/etc/letsencrypt/live'
NGINX_SITES = '/etc/nginx/sites-enabled'
NGINX_AVAILSITES = '/etc/nginx/sites-available'
NGINX_CHECK = 'nginx -t'
NGINX_RELOAD = 'sudo systemctl reload nginx'
CONSULTEMPLATE_RELOAD = 'sudo systemctl reload consul-template'
THIS_DIR = os.path.dirname(os.path.abspath(__file__))
CERTBOT_CREATECERT = "certbot certonly --webroot -w /usr/share/nginx/html/ -d %s --agree-tos --no-eff-email --no-redirect --keep --register-unsafely-without-email"
CERTBOT_DELETECERT = "certbot delete --cert-name %s"
TEMPLATE_WEBSITE = 'traveltool_website.j2'
TEMPLATE_SSL_WEBSITE = 'traveltool_ssl_website.j2'
TEMPLATE_REDIRECT = 'traveltool_redirect.j2'
TEMPLATE_AGENT = 'agent.j2'
TEMPLATE_ENVIRONMENT = Environment(
    autoescape=False,
    loader=FileSystemLoader(os.path.join(THIS_DIR)),
    trim_blocks=False)
TRAVELTOOL_WILDCARD = 'wildcard.traveltool.es'
ARRAYSERVERS = ['ttmadtrvprvp00v', 'ttmadtrvprvp01v', 'ttmadtrvprvp02v']
RELOAD_ENPOINT = '/configreload'
RELOAD_ENPOINT_CONSULTEMPLATE = '/configreloadconsultemplate'
VALIDIPS = ['213.130.43.55','213.130.43.119']

#-----------------------------------------------------------------------------
# Functions
#-----------------------------------------------------------------------------

def abortbybadrequest(text):
    app.logger.critical(text)
    flash(text,'error')
    abort(400)

def abortbyerror(text):
    app.logger.critical(text)
    flash(text,'error')
    abort(500)

def abortbycertrequest(text):
    app.logger.critical(text)
    flash(text,'error')
    abort(501)

def exec_command(cmd):
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    output, err = process.communicate()
    return process.returncode, output.decode("utf-8"), err.decode("utf-8")

def template_website(template, tmpdomain, tmpagencyId, tmpapplication, tmpcertificate):
    #logger.info("Starting website template")

    templateWebsite = os.path.join(THIS_DIR, template)
    if not os.path.exists(templateWebsite):
        message="Couldn't find template file " + templateWebsite
        abortbyerror(message)

    renderSite=TEMPLATE_ENVIRONMENT.get_template(template).render(domain = tmpdomain, agency = tmpagencyId, application = tmpapplication, certificate = tmpcertificate)
    #logger.debug("Output template render: %s", renderSite)

    if not os.path.exists(NGINX_SITES):
        message="Couldn't find Nginx sites folder " + NGINX_SITES
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

def template_website_redirect(template, tmpdomain, tmpredirectdomain, tmpcertificate):
    #logger.info("Starting website template")

    templateWebsite = os.path.join(THIS_DIR, template)
    if not os.path.exists(templateWebsite):
        message="Couldn't find template file " + templateWebsite
        abortbyerror(message)

    renderSite=TEMPLATE_ENVIRONMENT.get_template(template).render(domain = tmpdomain, redirectdomain = tmpredirectdomain, certificate = tmpcertificate)
    #logger.debug("Output template render: %s", renderSite)

    if not os.path.exists(NGINX_SITES):
        message="Couldn't find Nginx sites folder " + NGINX_SITES
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

def configreload_allservers():
    for item in ARRAYSERVERS:
        conn = http.client.HTTPConnection(item)
        app.logger.warning("Preparing to send reload to %s", item)
        try:
            conn.request("GET",RELOAD_ENPOINT)
            respconn = conn.getresponse()
            if respconn.status != 200:
                app.logger.warning("Error reloading nginx config from %s", item)
            else:
                app.logger.info("Reload nginx config OK from %s", item)
        except Exception as ex:
            app.logger.warning("Error trying to connect to %s - %s", item, ex)
        finally:
            conn.close()
    


def configreload_consultemplate_allservers():
    for item in ARRAYSERVERS:
        conn = http.client.HTTPConnection(item)
        try:
            conn.request("GET",RELOAD_ENPOINT_CONSULTEMPLATE)
      
            respconn = conn.getresponse()
            if respconn.status != 200:
                app.logger.warning("Error sending reload url to %s", item)
            else:
                app.logger.info("OK sending reload url to %s", item)
            conn.close()
        except:
            app.logger.warning("Error trying to connect to %s", item)



def checkparameters(argumentos):
    #app.logger.info("Checking input parameters...")

    action=''
    domain=''
    agencyId=''
    application=''
    agentName=''
    agentUrl=''
    newdomain=''
    forcessl='1'
    showlogs=''
    if 'command' in argumentos:
        action=argumentos['command']
        action=action.lower()
    if 'domain' in argumentos:
        domain=argumentos['domain']
        domain=domain.lower()
    if 'idagencia' in argumentos:
        agencyId=argumentos['idagencia']
    if 'application' in argumentos:
        application=argumentos['application']
        application=application.lower()
    if 'name' in argumentos:
        agentName=argumentos['name']
        agentName=agentName.lower()
    if 'url' in argumentos:
        agentUrl=argumentos['url']
        agentUrl=agentUrl.lower()
    if 'newdomain' in argumentos:
        newdomain=argumentos['newdomain']
        newdomain=newdomain.lower()
    if 'forcessl' in argumentos: 
        forcessl=argumentos['forcessl']
    #if 'forceSSL' in argumentos: 
    #    forcessl=argumentos['forceSSL']
    if 'showlogs' in argumentos: 
        showlogs=argumentos['showlogs']

    if action == "add":
        if not (action and domain and agencyId and application):
            message="Invalid parameters for action " + action + ". Required arguments: command, domain, idagencia, application" 
            abortbybadrequest(message)
        if ".traveltool." not in application:
            message="Invalid parameter for application: " + action + ". This paramater must be in form *.traveltool.*"
            abortbybadrequest(message)
    elif action == "del":
        if not (action and domain):
            message="Invalid parameters for action " + action + ". Required arguments: command, domain"
            abortbybadrequest(message)
    elif action == "change":
        if not (action and domain and agencyId and application and newdomain):
            message="Invalid parameters for action " + action + ". Required arguments: command, domain, idagencia, application, newdomain" 
            abortbybadrequest(message)
        if ".traveltool." not in application:
            message="Invalid parameter for application: " + action + ". This paramater must be in form *.traveltool.*"
            abortbybadrequest(message)
    elif action == "redirectdomain":
        if not (action and domain and newdomain):
            message="Invalid parameters for action " + action + ". Required arguments: command, domain, newdomain"
            abortbybadrequest(message)
    elif action == "addagent":
        if not (action and domain and agentName and agentUrl):
            message="Invalid parameters for action " + action + ". Required arguments: command, domain, name, url"
            abortbybadrequest(message)
    elif action == "delagent":
        if not (action and domain and agentName):
            message="Invalid parameters for action " + action + ". Required arguments: command, domain, name" 
            abortbybadrequest(message)
    else:
        message="action " + action + " not allowed" 
        abortbybadrequest(message)

    #app.logger.info("Checked input parameters")

    return action, domain, agencyId, application, newdomain, agentName, agentUrl, forcessl, showlogs

def checkSubdomainTraveltool (domain):

	#Check if subdomain Traveltool
	subdomainTraveltool = False

	#If traveltool domain, skip certification request (use wildcard)
	if ".traveltool." in domain:
		strRegex = re.compile('(.*).traveltool.', re.IGNORECASE)
		strFound = strRegex.match(domain)
		domainPreffix = strFound.group(1)
		if "." in domainPreffix:
			subdomainTraveltool = False
		else:
			subdomainTraveltool = True
			
	return subdomainTraveltool

def checkValidIp(domain):
    ipValida = False
    try:
        resolvIp = socket.gethostbyname(domain)
    except socket.gaierror:
        message="Error verifying ip for domain: " + domain
        abortbybadrequest(message)  
    except:
        message="Error verifying ip for domain: " + domain
        abortbybadrequest(message)  

    if resolvIp in VALIDIPS:
        ipValida = True

    return ipValida

def createdomain(domain, agencyId, application, forcessl):
    #logger.info("Creating new domain %s", domain)

    #Check if ipValid
    if not checkValidIp(domain):
        message="Error verifying ip for domain: " + domain
        abortbybadrequest(message)   

    #Remove domain if exits
    siteFile = os.path.join(NGINX_SITES, domain + ".conf")
    if os.path.exists(siteFile):
        message="Web for " + domain + " exists. Call to change method is needed"
        abortbyerror(message)
    
    if not checkSubdomainTraveltool(domain):
        #Check if certificate folder exists
        if not os.path.exists(CERT_FOLDER):
            message="Couldn't find certificate folder " + CERT_FOLDER
            abortbyerror(message)

        #Check if certificate exists
        certDomain = os.path.join(CERT_FOLDER, domain + "/cert.pem")
        if not os.path.exists(certDomain):
            #logger.info("Couldn't find certificate for domain %s", certDomain)

            #Execute certbot and check if certificate exists
            strCmd = CERTBOT_CREATECERT % domain
            resultCode, resultOutput, resultError = exec_command(strCmd)
            if not (resultCode == 0):
                message="Error executing certbot request for domain: " + domain + ". Output: " + resultError
                abortbycertrequest(message)
        #logger.info (resultOutput)
        certificate = domain
    else:
        certificate = TRAVELTOOL_WILDCARD

    #Template nginx site
    if forcessl == '1':
        template = TEMPLATE_SSL_WEBSITE
        template_website(template, domain, agencyId, application, certificate)
    else:
        template = TEMPLATE_WEBSITE
        template_website(template, domain, agencyId, application, certificate)

    #Check nginx config and reload

    #logger.info("Created new domain %s", domain)

    return

def deletedomain(action,domain,removeSsl=False):
    #logger.info("Deleting domain %s ...", domain)

    #delete website config
    siteFile = os.path.join(NGINX_SITES, domain + ".conf")
    if os.path.exists(siteFile):
        try:
            os.remove(siteFile)
            #logger.info("Deleted website for domain %s",domain)
        except:
            message="Unexpected error deleting website file. Error: " + sys.exc_info()[0]
            abortbyerror(message)
    else:
        #logger.warning("Site file doesn't exist: %s",siteFile)
        app.logger.warning("Site file doesn't exist: %s", siteFile)

    #only if action delete, if action change not delete certificate
    if action == "del":   
        if not checkSubdomainTraveltool(domain):
            #Check if certificate exists
            certDomain = os.path.join(CERT_FOLDER, domain)
            if not os.path.exists(certDomain):
                #logger.warning("Couldn't find certificate for domain %s", certDomain)
                app.logger.warning("Couldn't find certificate for domain %s", certDomain)
            else:
                strCmd = CERTBOT_DELETECERT % domain
                resultCode, resultOutput, resultError = exec_command(strCmd)
                if not (resultCode == 0):
                    #logger.warning("Error executing certbot delete for domain: %s", resultOutput)
                    app.logger.warning("Error executing certbot delete for domain: %s. Output: %s", domain, resultError)
    else:
        #in case change, we need to reload the config
        configreload_allservers()

    #logger.info("Deleted domain %s",domain)

    return

def changedomain(domain, agencyId, application, newdomain, forcessl):
    #logger.info("Changing website configuration for domain %s ...", domain)

    if domain == newdomain:
        deletedomain("change",domain)
    else:
        deletedomain("change",domain,True)
    createdomain(newdomain,agencyId,application,forcessl)

    #logger.info("Changed website configuration for domain %s", domain)

    return

def redirectdomain(domain, newdomain):
    #logger.info("Creating new domain %s", domain)

    #Check if ipValid
    if not checkValidIp(domain):
        message="Error verifying ip for domain: " + domain
        abortbybadrequest(message)   

    if not checkSubdomainTraveltool(domain):
        #Check if certificate folder exists
        if not os.path.exists(CERT_FOLDER):
            message="Couldn't find certificate folder " + CERT_FOLDER
            abortbyerror(message)

        #Check if certificate exists
        certDomain = os.path.join(CERT_FOLDER, domain + "/cert.pem")
        if not os.path.exists(certDomain):
            #logger.info("Couldn't find certificate for domain %s", certDomain)

            #Execute certbot and check if certificate exists
            strCmd = CERTBOT_CREATECERT % domain
            resultCode, resultOutput, resultError = exec_command(strCmd)
            if not (resultCode == 0):
                message="Error executing certbot request for domain: " + domain + ". Output: " + resultError
                abortbycertrequest(message)
        #logger.info (resultOutput)
        certificate = domain
    else:
        certificate = TRAVELTOOL_WILDCARD

    #Template nginx site
    template = TEMPLATE_REDIRECT
    template_website_redirect(template, domain, newdomain, certificate)

    #Check nginx config and reload

    #logger.info("Created new domain %s", domain)

    return

def addagent(domain, agentName, agentUrl):
    #logger.info("Creating new agent %s ...", agentName)

    #Check if domain file exist
    siteFile = os.path.join(NGINX_SITES, domain + ".conf")
    if not os.path.exists(siteFile):
        message="Couldn't find site file for domain: " + domain
        abortbybadrequest(message)

    #Template agent file
    templateAgent = os.path.join(THIS_DIR, TEMPLATE_AGENT)
    if not os.path.exists(templateAgent):
        message="Couldn't find template file " + templateAgent
        abortbyerror(message)
    renderAgent = TEMPLATE_ENVIRONMENT.get_template(TEMPLATE_AGENT).render(name = agentName, url = agentUrl)

    #Create agent File
    agentDomainFolder =  os.path.join(NGINX_AVAILSITES, domain + ".d/") 
    if not os.path.exists(agentDomainFolder):
        #logger.warning("Couldn't find agent folder for domain %s", agentDomainFolder)
        try: 
            os.makedirs(agentDomainFolder)
        except: 
            message="Unexpected error creating agent folder. Error: " + sys.exc_info()[0]
            abortbyerror(message)
    agentFile =  os.path.join(NGINX_AVAILSITES, domain + ".d/", agentName + ".conf")
    if os.path.exists(agentFile):
        try:
            os.remove(agentFile)
        except:
            message="Unexpected error deleting agent file. Error: " + sys.exc_info()[0]
            abortbyerror(message)
    try:
        #logger.info("Creating file for agent: %s", agentFile)
        with open(agentFile, 'w') as f:
            f.write(renderAgent)
    except:
        message="Unexpected error creating agent file. Error: " + sys.exc_info()[0]
        abortbyerror(message)

    return

def delagent(domain, agentName):
    #logger.info("Starting to delete agent: %s ...", agentName)

    agentFile =  os.path.join(NGINX_AVAILSITES, domain + ".d/", agentName + ".conf")
    try:
        os.remove(agentFile)
    except:
        message="Unexpected error deleting agent file. Error: " + sys.exc_info()[0]
        abortbyerror(message)

    return



 ### ROUTES ###
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(400)
def custom400(error):
    ts = strftime('[%Y-%b-%d %H:%M]')
    app.logger.info('%s %s %s %s %s %s',
                    ts,
                    request.remote_addr,
                    request.method,
                    request.scheme,
                    request.full_path,
                    str(error))
    return render_template('400.html'),400

@app.errorhandler(500)
def custom500(error):
    ts = strftime('[%Y-%b-%d %H:%M]')
    app.logger.info('%s %s %s %s %s %s',
                    ts,
                    request.remote_addr,
                    request.method,
                    request.scheme,
                    request.full_path,
                    str(error))
    return render_template('500.html'),500

@app.errorhandler(501)
def custom501(error):
    ts = strftime('[%Y-%b-%d %H:%M]')
    app.logger.info('%s %s %s %s %s %s',
                    ts,
                    request.remote_addr,
                    request.method,
                    request.scheme,
                    request.full_path,
                    str(error))
    return render_template('501.html'),501

@app.route('/', methods = ['GET'])
def web_root():
    return 'OK'
#    resp = make_response(render_template('error.html'), 404)
#    resp.headers['X-Reason'] = 'Page not found'
#    return resp

#MIGRATION COMPATIBILITY
@app.route('/configuration', methods = ['GET','POST'])
@app.route('/reverseproxy/configuration.php', methods = ['GET','POST'])
def configuration():
    action, domain, agencyId, application, newdomain, agentName, agentUrl, forcessl, showlogs=checkparameters(request.args)

    if not domain.startswith("www.traveltool."):
        ### COMMAND ###
        if action == "add":
            #logger.debug("create domain")
            createdomain(domain,agencyId,application,forcessl)
            #migracion#configreload_allservers()
        elif action == "del":
            #logger.debug("delete domain")
            deletedomain(action,domain)
            #migracion#configreload_allservers()
        elif action == "change":
            #logger.debug("change domain")
            changedomain(domain,agencyId,application,newdomain,forcessl)
            #migracion#configreload_allservers()
        elif action == "redirectdomain":
            #logger.debug("change domain")
            redirectdomain(domain,newdomain)
        elif action == "addagent":
            #logger.debug("add agent")
            addagent(domain, agentName, agentUrl)
            #migracion#configreload_allservers()
        elif action == "delagent":
            #logger.debug("delete agent")
            delagent(domain, agentName)
            #migracion#configreload_allservers()
        else:
            message="Action " + action + " not allowed"
            abortbybadrequest(message)

        return render_template('response.html',showlogs=showlogs),200
    else:
        message="Domain not allowed: " + domain + ". Own domain is required."
        abortbybadrequest(message)

@app.route('/configreload', methods = ['GET'])
def config_reload():
    resultCode, resultOutput, resultError = exec_command(NGINX_RELOAD)
    if not (resultCode == 0):   
        message="Error reloading Nginx's configuration: " + resultError
        abortbyerror(message)
    else:
        return 'Reload: OK'

@app.route('/configreloadconsultemplate', methods = ['GET'])
def config_reload_consultemplate():
    resultCode, resultOutput, resultError = exec_command(CONSULTEMPLATE_RELOAD)
    if not (resultCode == 0):   
        message="Error reloading Consul-template's configuration: " + resultError
        abortbyerror(message)
    else:
        return 'Reload: OK'

@app.route('/configreloadcluster/nginx', methods = ['GET'])
def config_reloadcluster_nginx():
    configreload_allservers()
    return 'Reload: OK'

@app.route('/configreloadcluster/consultemplate', methods = ['GET'])
def config_reloadcluster_consultemplate():
    configreload_consultemplate_allservers()
    return 'Reload: OK'

@app.route('/configreloadcluster/health-check', methods = ['GET'])
def config_reloadcluster_healthcheck():
    return 'OK'

### LOGGING ROUTING
@app.after_request
def after_request(response):
    # Note: we treat 500 in other place
    # This IF avoids the duplication of registry in the log,
    # since that 500 is already logged via @app.errorhandler.
    ts = strftime('[%Y-%b-%d %H:%M]')
    app.logger.info('%s %s %s %s %s %s',
                    ts,
                    request.remote_addr,
                    request.method,
                    request.scheme,
                    request.full_path,
                    response.status)
    return response

@app.errorhandler(Exception)
def exceptions(e):
    ts = strftime('[%Y-%b-%d %H:%M]')
    app.logger.info('%s %s %s %s %s 5xx INTERNAL SERVER ERROR\n%s',
                  ts,
                  request.remote_addr,
                  request.method,
                  request.scheme,
                  request.full_path,
                  str(e))
    return "Internal Server Error", 500

### MAIN ###
if __name__ == '__main__':
    app.run()