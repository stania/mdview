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
import mimetypes
import codecs
import urllib
from jinja2 import Template

from cherrypy.lib.static import serve_file, staticdir, serve_fileobj

markdowner = markdown2.Markdown()

debug = False

server_port = 7559

RES_ID = {}

def main_is_frozen():
    return (hasattr(sys, "frozen") or
            hasattr(sys, "importers") or
            imp.is_frozen("__main__"))

def get_base_dir():
    return base_dir

if main_is_frozen():
    RES_ID = resource.res_id_dict()

def get_res_data(path):
    if main_is_frozen():
        path = path.replace("/", "\\")
        if RES_ID.has_key(path):
            res = win32api.LoadResource(0, u'RESOURCE', RES_ID[path])
            return StringIO.StringIO(res).read()
        else:
            return None
    else:
        return open(os.path.join(get_base_dir(), ".res", path)).read()

def get_content_type(path):
    guess = mimetypes.guess_type(path)[0]
    if guess != None:
        return guess
    elif os.path.splitext(path)[-1] == ".md":
        return "text/plain"
    else:
        return "application/octet-stream"


def get_resource(path):
    if main_is_frozen():
        path = path.replace("/", "\\")
        if RES_ID.has_key(path):
            return serve_fileobj(
                StringIO.StringIO(win32api.LoadResource(0, u'RESOURCE', RES_ID[path])),
                content_type=get_content_type(path)
                )
        else:
            raise cherrypy.NotFound
    else:
        return serve_file(os.path.join(get_base_dir(), path))

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
        result += "<p>This program renders *.md with Markdown renderer.</p>\n"
        result += "<ul>\n"
        md_exists = False
        if subpath != basedir:
            result += """\t<li><a href="..">..</a></li>\n"""
        for entry in entries:
            if entry is ".":
                continue
            if entry.endswith(".md"):
                md_exists = True
            result += """\t<li><a href="{}">{}</a></li>\n""".format(entry, entry)
        result += "</ul>\n"
        if not md_exists:
            result += "<p>You don't have any Markdown document! You can start with creating Markdown document within same directory with server.exe</p>"
        return result
        
    def cmd_handler(self, *args, **kwargs):
        if len(args) > 0 and args[0] == ".res":
            return get_resource("/".join(args))
        else:
            raise cherrypy.NotFound
    
    def render_markdown(self, path):
        f = None
        try:
            f = open(os.path.join(get_base_dir(), path), "rb")
            data = f.read()
            try: 
                data = data.decode("utf-8")
            except:
                print "file is mbcs"
                data = data.decode("mbcs")
            return markdowner.convert(data.encode("utf-8"))
        finally:
            if f: f.close()

    @cherrypy.expose
    def default(self, *args, **kwargs): # fallback
        template = Template(get_res_data(".res/default.html"))
        return self.default_dispatcher(template, args, **kwargs)

    def default_dispatcher(self, template, args, **kwargs):
        if kwargs.has_key("ar"):
            if debug: print "/".join(["/ar"] + list(args))
            raise cherrypy.HTTPRedirect("/".join(["/ar"] + list(args)))
        if len(args) > 0 and args[0][0] is '.':
            return self.cmd_handler(*args, **kwargs)
        subpath = "/".join(args)
        subpath = subpath.decode("utf-8")
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
        template = Template(get_res_data(".res/ar.html"))
        return self.default_dispatcher(template, args, **kwargs)
        
    @cherrypy.expose
    def wfc(self, *args, **kwargs): #wait for change
        subpath = "/".join(args)
        subpath = subpath.decode("utf-8")
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

class MutexException(BaseException):
    pass

mutex_handle = None
class single_instance():
    def __init__(self):
        global mutex_handle
        ERROR_ALREADY_EXISTS = 183
        mutex_handle = win32event.CreateMutex(None, 1, "MDVIEW")
        if mutex_handle and win32api.GetLastError() is ERROR_ALREADY_EXISTS:
            raise MutexException()
        else:
            print "mutex created", mutex_handle
    
t = None
try: 
    me = single_instance()
    base_dir = os.getcwd()
    print "base directory:", base_dir
    cherrypy.tree.mount(Root())
    cherrypy.server.socket_port = server_port
    cherrypy.engine.blocking = False
    cherrypy.engine.start()
    t = threading.Thread(target=lambda: webbrowser.open("http://localhost:"+str(server_port)))
    t.start()
    cherrypy.engine.block()
except MutexException:
    pass
finally:
    if not t:
        t = threading.Thread(target=lambda: webbrowser.open("http://localhost:"+str(server_port)))
        t.start()
        

