# Copyright (C) 2014 Claudio Guarnieri.
# This file is part of Detekt - https://github.com/botherder/detekt
# See the file 'LICENSE' for copying permission.

import sys
import Queue
import random
import threading

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4.QtWebKit import *

from bottle import *
from utils import get_resource, check_connection
import detector

# Add the gui folder to the template path of bottoe.py.
TEMPLATE_PATH.insert(0, get_resource('gui'))

# Instatiate the Bottle application.
webapp = Bottle()

# This queue will contain the list of matches retrieved from the yara scan.
queue_results = Queue.Queue()
# This queue will contain the list of errors generated by the detector.
queue_errors = Queue.Queue()

# Instatiate the thread that will run the detector.
scanner = threading.Thread(target=detector.main, args=(queue_results, queue_errors))
scanner.daemon = True

# Enabled language.
lang = 'en'

# Port for the web server.
web_port = random.randint(1024, 65535)

# This route serves static content such as images, css and js files.
@webapp.route('/static/<path:path>')
def static(path):
    return static_file(path, get_resource('gui/static/'))

# This route returns the start page.
@webapp.route('/')
def index():
    connection = check_connection()
    return template('index.{0}'.format(lang), language=lang, action='start', connection=connection)

@webapp.route('/language', method='POST')
def language():
    global lang
    lang = request.forms.get('language')
    redirect('/')

# This route triggers the execution of the detector then returns the running
# page which will then start refreshing to /check.
@webapp.route('/scan')
def scan():
    scanner.start()
    return template('index.{0}'.format(lang), action='running')

# This route checks whether the scanner thread has finished, and if so it
# will collect errors and results and return the results page.
@webapp.route('/check')
def check():
    if scanner.isAlive():
        return template('index.{0}'.format(lang), action='running')
    else:
        # Flag if the detector generated any matches.
        infected = False
        if queue_results.qsize() > 0:
            infected = True

        # Populate the list of errors from the queue.
        errors = []
        while True:
            try:
                errors.append(queue_errors.get(block=False))
            except Queue.Empty:
                break

        # Populate the list of results from the queue.
        results = []
        while True:
            try:
                # Retrieve next entry in the results queue.
                entry = queue_results.get(block=False)
                # Only add the detection name to the list of results.
                # This is to avoid to have the rules names in there, which
                # will mostly be meaningless to a regular user.
                if entry['detection'] not in results:
                    results.append(entry['detection'])
            except Queue.Empty:
                break

        return template('index.{0}'.format(lang), action='results', infected=infected,
                        errors=errors, results=results)

# This thread will run the bottle.py web app. I should probably randomize
# the port or make it configurable?
class WebApp(QThread):
    def __init__(self):
        QThread.__init__(self)

    def run(self):
        run(webapp, host='localhost', port=web_port, quiet=True)

# Define the Qt window, resizable and that connect to the bottle.py app.
class Window(QWebView):
    def __init__(self):
        QWebView.__init__(self)
        self.setWindowTitle('Detekt')
        self.resize(640, 500)
        self.load(QUrl('http://localhost:{0}/'.format(web_port)))

def main():
    # Initiate the Qt application.
    app = QApplication(sys.argv)

    # Instantiate and start the bottle.py application.
    web = WebApp()
    web.start()

    # Instantiate and show the Qt window.
    win = Window()
    win.show()

    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
