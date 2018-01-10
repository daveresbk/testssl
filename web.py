from flask import Flask, url_for, request, make_response, Response, render_template, abort, jsonify, flash
import logging
from logging.handlers import RotatingFileHandler
app = Flask(__name__)

def abortbyerror(text):
    app.logger.critical(text)
    flash(text,'error')
    abort(500)
    
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
            message="Invalid parameters for action %s. Required arguments: action, domain, agencyid, application" % action
            abortbyerror(message)
    elif action == "delete":
        if not (action and domain):
            message="Invalid parameters for action %s. Required arguments: action, domain" % action
            abortbyerror(message)
    elif action == "change":
        if not (action and domain and agencyId and application):
            message="Invalid parameters for action %s. Required arguments: action, domain, agencyid, application" % action
            abortbyerror(message)
    elif action == "addagent":
        if not (action and domain and agentName and agentUrl):
            message="Invalid parameters for action %s. Required arguments: action, domain, agentname, agenturl" % action
            abortbyerror(message)
    elif action == "delagent":
        if not (action and domain and agentName):
            message="Invalid parameters for action %s. Required arguments: action, domain, agentname" % action
            abortbyerror(message)
    else:
        message="action %s no allowed" % action
        abortbyerror(message)

    app.logger.info("Checked input parameters")

    return action, domain, agencyId, application, agentName, agentUrl, forcessl, showlogs

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