from web import app
from logging.handlers import RotatingFileHandler
import logging

#-----------------------------------------------------------------------------
###Setup###
# gunicorn
#-----------------------------------------------------------------------------

if __name__ == "__main__":
    logHandler = RotatingFileHandler('info.log', maxBytes=1000, backupCount=10)
    # set the log handler level
    logHandler.setLevel(logging.INFO)
    # set the app logger level
    app.logger.setLevel(logging.INFO)
    app.logger.addHandler(logHandler)    
    app.secret_key = 'traveltool'
    app.run()