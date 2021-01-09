try:
    import asyncio
except ImportError:
    raise RuntimeError("This example requries Python3 / asyncio")

import os
import sys
import importlib
from threading import Thread

from flask import Flask, render_template, redirect
from jinja2 import Environment, FileSystemLoader
from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop

from bokeh.application import Application
from bokeh.application.handlers import FunctionHandler
#from bokeh.application.handlers import DirectoryHandler
from bokeh.embed import server_document
from bokeh.server.server import BaseServer
from bokeh.server.tornado import BokehTornado
from bokeh.server.util import bind_sockets
from bokeh.themes import Theme
from bokeh.settings import settings
from bokeh.io import curdoc

from _templates import jinja_templates

#make git submodule path visible
sys.path.append('terrain-corrector')
#side-step '-' with importlib
app_source = importlib.import_module('..app', 'terrain-corrector.subpkg')

if __name__ == '__main__':
    print('This script is intended to be run with gunicorn. e.g.')
    print()
    print('    gunicorn -w 4 flask_gunicorn:app')
    print()
    print('will start the app on four processes')
    import sys
    sys.exit()

app = Flask(__name__)
settings.resources = 'cdn'
settings.resources = 'inline'
settings.log_level = 'trace'

@app.route('/')
def redir():
    return redirect('/about/')

@app.route('/about/')
def about_page():
    return render_template("about.html")


def bkapp(doc):
    app_source.react.server_doc(doc)
    '''
    for root in doc.roots:
        if ID == :
            root.tags.append('header')
        elif    :
            root.tags.append('nav')
        elif    :
            root.tags.append('main')
    '''
    
# can't use shortcuts here, since we are passing to low level BokehTornado
bkapp = Application(FunctionHandler(bkapp))
#directory_app = os.path.join(os.getcwd(), 'terrain-corrector')
#bkapp = Application(DirectoryHandler(filename=directory_app))

# allows each gunicorn worker process to listen on its own port
#sockets, port = bind_sockets("localhost", 0) #-> chooses its own port
sockets, port = bind_sockets("localhost", 5006) #i choose the port


bokeh_doc = app_source.react.server_doc()
context = bokeh_doc.template_variables

@app.route('/terrain-corrector/', methods=['GET'])
def bkapp_page():
    
    local_port = 'http://localhost:%d' % port
    docs = [server_document(local_port + '/bkapp')]
    base = jinja_templates['file']
    _render_items = app_source.react._render_items
    _render_items['location'] = bokeh_doc.roots[0].to_json(include_defaults=True)
    #css_files = [app_source.react._css]

    return render_template('react.html', base=base, docs=docs, roots=_render_items, 
                            local_port=local_port, **jinja_templates, **context)

def bk_worker():
    asyncio.set_event_loop(asyncio.new_event_loop())

    bokeh_tornado = BokehTornado({'/bkapp': bkapp}, extra_websocket_origins=["127.0.0.1:8000", "localhost:5006"])
    bokeh_http = HTTPServer(bokeh_tornado)
    bokeh_http.add_sockets(sockets)

    server = BaseServer(IOLoop.current(), bokeh_tornado, bokeh_http)
    server.start()
    server.io_loop.start()

t = Thread(target=bk_worker)
t.daemon = True
t.start()