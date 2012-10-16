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
import webbrowser
import threading
import glob
import mimetypes
import codecs
import urllib
from jinja2 import Template

import resource
from settings import load_settings

from cherrypy.lib.static import serve_file, staticdir, serve_fileobj

markdowner = markdown2.Markdown()


settings = load_settings()

RES_ID = {}

def main_is_frozen():
    return (hasattr(sys, "frozen") or
            hasattr(sys, "importers") or
            imp.is_frozen("__main__"))

def get_base_dir():
    return settings.base_dir

def get_res_dir():
    return settings.res_dir

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
        return open(os.path.join(get_res_dir(), path)).read()

def get_content_type(path):
    guess = mimetypes.guess_type(path)[0]
    if guess != None:
        return guess
    elif os.path.splitext(path)[-1] == ".md":
        return "text/plain"
    else:
        return "application/octet-stream"


def endswith_md_ext(p):
    return any(p.endswith(_) for _ in settings.md_exts)


def serve_resource(path):
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
        return serve_file(os.path.abspath(os.path.join(get_res_dir(), path)))

class Root(object):
    @classmethod
    def _get_subpath(cls, args):
        if len(args) > 0 and args[0] is "":
            args = args[1:]
        subpath = urllib.unquote("/".join(args))
        if type(subpath) == str:
            subpath = subpath.decode("utf-8")
        return subpath
        
    def find_indexfile(self, *args):
        basedir = self._get_subpath(args)
        for entry in ["index.html"] + ["index" + _ for _ in settings.md_exts]:
            if os.path.exists(os.path.join(basedir, entry)):
                return entry
        return None

    def dir_handler(self, basedir, subpath):
        abspath = os.path.join(basedir, subpath)
        abspath = os.path.normpath(abspath)

        if not abspath.startswith(basedir):
            raise cherrypy.HTTPError(403)

        if self.find_indexfile(abspath):
            print "index found", self.find_indexfile(abspath), "/".join([abspath, self.find_indexfile(abspath)])
            indexpath = self._get_subpath(abspath) + "/" + self.find_indexfile(abspath)
            raise cherrypy.HTTPRedirect(indexpath)

        result = u""
        result += u"<p>This program renders {} with Markdown renderer.</p>\n".format(str(settings.md_exts))
        result += u"<ul>\n"

        md_exists = False

        # if abspath contains non-ascii char, type(abspath) is unicode. unless, str.
        # let's make it as same type
        if type(abspath) == str:
            abspath = abspath.decode("utf-8")
        # below here, abspath is now unicode

        entries = os.listdir(abspath)
        if abspath != basedir:
            href = os.path.dirname(subpath)
            result += u"""\t<li><a href="/{}">../</a></li>\n""".format(href)

        for entry in entries:
            entry4user = entry
            if entry is u".":
                continue
            if endswith_md_ext(entry):
                md_exists = True
            if os.path.isdir(os.path.join(abspath, entry)):
                entry4user += u"/"
            href = self._get_subpath([subpath, entry])
            if len(href) > 0 and href[0] != "/":
                href = "/" + href
            result += u"""\t<li><a href="{}">{}</a></li>\n""".format(href, entry4user)
        result += u"</ul>\n"

        if not md_exists:
            result += u"<p>You don't have any Markdown document! You can start with creating Markdown document within same directory with executable(ex: mdview.exe)</p>"

        template = Template(get_res_data("dirindex.html"))
        return template.render(path=abspath, contents=result)
        
    def cmd_handler(self, *args, **kwargs):
        if len(args) > 0 and args[0] == settings.RES_PATH:
            return serve_resource(self._get_subpath(args[1:]))
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
        template = Template(get_res_data("default.html"))
        return self.default_dispatcher(template, args, **kwargs)

    def default_dispatcher(self, template, args, **kwargs):
        if kwargs.has_key("ar"):
            _subpath = self._get_subpath(["/ar"] + list(args))
            if settings.debug: print _subpath
            raise cherrypy.HTTPRedirect(_subpath)
        if len(args) > 0 and args[0][0] is '.':
            return self.cmd_handler(*args, **kwargs)
        subpath = self._get_subpath(args)
        if settings.debug: print "default:", subpath
        if endswith_md_ext(subpath):
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
        subpath = self._get_subpath(args)
        if not endswith_md_ext(subpath):
            raise cherrypy.HTTPRedirect(subpath)
        template = Template(get_res_data("ar.html"))
        return self.default_dispatcher(template, args, **kwargs)

    @cherrypy.expose
    def wfc(self, *args, **kwargs): #wait for change
        subpath = self._get_subpath(args)
        if settings.debug: print "wfc:", subpath
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
    if not settings.debug:
        print "RUNNING IN PRODUCTION MODE"
    print "base directory:", settings.base_dir
    cherrypy.tree.mount(Root())
    cherrypy.server.socket_port = settings.server_port
    cherrypy.engine.blocking = False
    cherrypy.engine.start()
    t = threading.Thread(target=lambda: webbrowser.open("http://localhost:"+str(settings.server_port)))
    t.start()
    cherrypy.engine.block()
except MutexException:
    pass
finally:
    if not t:
        t = threading.Thread(target=lambda: webbrowser.open("http://localhost:"+str(settings.server_port)))
        t.start()
        

