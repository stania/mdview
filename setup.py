#!/cygdrive/c/Python27/python.exe
from distutils.core import setup
import py2exe
import resource

resource.gen_reslist_py()

py2exe_options = dict(
    includes=['_reslist'],
    packages=["encodings", "email", "BaseHTTPServer", "httplib", "Cookie"],
    excludes=[#'_ssl',  # Exclude _ssl
              'pyreadline', 'difflib', 'doctest', 'locale',
              'pickle', 'calendar'],  # Exclude standard library
    dll_excludes=['msvcr71.dll', "w9xpopen.exe", 'mswsock.dll', 'powrprof.dll'],  # Exclude msvcr71
    compressed=True,  # Compress library.zip
    bundle_files=1,
    dist_dir=".",
    )

print resource.py2exe_list()

setup(console=[{
            'script': "server.py", 
            'other_resources': resource.py2exe_list()
                }], 
        zipfile=None,
        options={'py2exe': py2exe_options},)
