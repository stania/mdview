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
import glob
from tendo import singleton
from jinja2 import Template

from cherrypy.lib.static import serve_file, staticdir

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
    def find_indexfile(self, *args):
        basedir = "/".join(args)
        for entry in ["index.html", "index.md"]:
            if os.path.exists(os.path.join(basedir, entry)):
                return entry
        return None

    def dir_handler(self, basedir, *args):
        subpath = os.path.join(basedir, *args)
        subpath = os.path.normpath(subpath)
        if not subpath.startswith(basedir):
            raise cherrypy.HTTPError(403)
        if self.find_indexfile(subpath):
            print "index found", self.find_indexfile(subpath), "/".join([subpath, self.find_indexfile(subpath)])
            indexpath = "/".join(args) + "/" + self.find_indexfile(subpath)
            raise cherrypy.HTTPRedirect(indexpath)
        result = ""
        entries = os.listdir(subpath)
        result += "<ul>\n"
        if subpath is not basedir:
            result += """\t<li><a href="..">..</a></li>\n"""
        for entry in entries:
            if entry is ".":
                continue
            result += """\t<li><a href="{}">{}</a></li>\n""".format(entry, entry)
        result += "</ul>"
        return result
        
    def cmd_handler(self, *args, **kwargs):
        if len(args) > 0 and args[0] is ".res":
            return get_resource("/".join(args[1:]))
        pass
    
    def render_markdown(self, path):
        f = None
        try:
            f = open(os.path.join(get_base_dir(), path))
            return markdowner.convert(f.read())
        except:
            raise cherrypy.HTTPError(500)
        finally:
            if f: f.close()

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
        elif os.path.isdir(os.path.join(get_base_dir(), subpath)):
            return self.dir_handler(get_base_dir(), subpath)
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
        return self.default_dispatcher(None, args, **kwargs)
    
t = None
try: 
    me = singleton.SingleInstance()
    print "asdf"
    base_dir = os.getcwd()
    print "base directory:", base_dir
    cherrypy.tree.mount(Root())
    cherrypy.server.socket_port = server_port
    cherrypy.engine.blocking = False
    cherrypy.engine.start()
    t = threading.Thread(target=lambda: webbrowser.open("http://localhost:"+str(server_port)))
    t.start()
    cherrypy.engine.block()
finally:
    if not t:
        t = threading.Thread(target=lambda: webbrowser.open("http://localhost:"+str(server_port)))
        t.start()
        

