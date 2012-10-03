'''
Created on 2012. 9. 30.

@author: stania

'''

import cherrypy
import markdown2
import os, time
import win32api
import win32event
import pywintypes
from jinja2 import Template

from cherrypy.lib.static import serve_file

markdowner = markdown2.Markdown()

debug = False

def get_base_dir():
    return base_dir

def get_resource(path):
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
        if kwargs.has_key("ar"):
            if debug: print "/".join(["/ar"] + list(args))
            raise cherrypy.HTTPRedirect("/".join(["/ar"] + list(args)))
        if len(args) > 0 and args[0][0] is '.':
            self.cmd_handler(*args, **kwargs)
        subpath = "/".join(args)
        if debug: print "default:", subpath
        if subpath.endswith(".md"):
            return self.render_markdown(subpath)
        else:
            return serve_file(os.path.join(get_base_dir(), subpath))
        
    @cherrypy.expose
    def ar(self, *args, **kwargs):
        template = Template(open(os.path.join(get_base_dir(), ".res", "ar.html")).read())
        subpath = "/".join(args)
        if not subpath.endswith(".md"):
            raise cherrypy.HTTPRedirect(subpath)
        return template.render(path=subpath, contents=self.render_markdown(subpath))
        
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
            return self.default(*args, **kwargs)
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
cherrypy.engine.start()
cherrypy.server.socket_port = 8080
cherrypy.server.start()
#webbrowser.open("http://localhost:8080")
print "open browser"
cherrypy.engine.block()

