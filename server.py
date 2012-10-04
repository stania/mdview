'''
Created on 2012. 9. 30.

@author: stania

'''

import cherrypy
import markdown2
import os, time, sys, imp
import win32api
import win32event
import pywintypes
import StringIO
import resource
import webbrowser
import threading
from jinja2 import Template

from cherrypy.lib.static import serve_file

markdowner = markdown2.Markdown()

debug = False

server_port = 8080

RES_ID = {}

def main_is_frozen():
    return (hasattr(sys, "frozen") or
            hasattr(sys, "importers") or
            imp.is_frozen("__main__"))

def get_base_dir():
    return base_dir

if main_is_frozen():
    RES_ID = resource.res_id_dict()

def get_resource(path):
    if main_is_frozen():
        if RES_ID.has_key(path):
            return serve_fileobj(StringIO(LoadResource(0, u'RESOURCE', RES_ID[path])))
        else:
            raise cherrypy.NotFound

    else:
        return serve_file(os.path.join(get_base_dir(), ".res", path))

class Root(object):
    def cmd_handler(self, args, kwargs):
        if len(args) > 0 and args[0] is ".res":
            return get_resource("/".join(args[1:]))
        pass
    
    def render_markdown(self, path):
        try:
            f = open(os.path.join(get_base_dir(), path))
            return markdowner.convert(f.read())
        except:
            raise cherrypy.HTTPError(500)
        finally:
            f.close()

    @cherrypy.expose
    def default(self, *args, **kwargs): # fallback
        template = Template(open(os.path.join(get_base_dir(), ".res", "default.html")).read())
        return self.default_dispatcher(template, args, **kwargs)

    def default_dispatcher(self, template, args, **kwargs):
        if kwargs.has_key("ar"):
            if debug: print "/".join(["/ar"] + list(args))
            raise cherrypy.HTTPRedirect("/".join(["/ar"] + list(args)))
        if len(args) > 0 and args[0][0] is '.':
            self.cmd_handler(*args, **kwargs)
        subpath = "/".join(args)
        if debug: print "default:", subpath
        if subpath.endswith(".md"):
            if template:
                return template.render(path=subpath, contents=self.render_markdown(subpath))
            else:
                return self.render_markdown(subpath)
        else:
            return serve_file(os.path.join(get_base_dir(), subpath))
        
    @cherrypy.expose
    def ar(self, *args, **kwargs):
        subpath = "/".join(args)
        if not subpath.endswith(".md"):
            raise cherrypy.HTTPRedirect(subpath)
        template = Template(open(os.path.join(get_base_dir(), ".res", "ar.html")).read())
        return self.default_dispatcher(template, args, **kwargs)
        
    @cherrypy.expose
    def wfc(self, *args, **kwargs): #wait for change
        subpath = "/".join(args)
        if debug: print "wfc:", subpath
        f = os.path.abspath(os.path.join(get_base_dir(), subpath))
        parent = os.path.dirname(f)
        timeout = kwargs.has_key("timeout") and int(kwargs["timeout"]) or 60000
        try:
            print "watching", f
            handle = win32api.FindFirstChangeNotification(parent, 0, 0x010)
            ret = win32event.WaitForSingleObject(handle, int(timeout))
            if ret is win32event.WAIT_TIMEOUT:
                raise cherrypy.HTTPError(304) 
            time.sleep(0.2)
            return self.default_dispatcher(None, args, **kwargs)
        except pywintypes.error as e: #@UndefinedVariable
            print e[2]
            raise cherrypy.HTTPError(500)
        finally:
            if handle:
                win32api.FindCloseChangeNotification(handle)
    
    @cherrypy.expose
    def index(self, *args, **kwargs):
        return "specify path"
    
base_dir = os.getcwd()
print "base directory:", base_dir
cherrypy.tree.mount(Root())
cherrypy.server.socket_port = server_port
cherrypy.engine.blocking = False
cherrypy.engine.start()
t = threading.Thread(target=lambda: webbrowser.open("http://localhost:"+str(server_port)))
t.start()
print "engine started"
cherrypy.engine.block()

