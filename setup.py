from distutils.core import setup
import py2exe

py2exe_options = dict(
    packages=["encodings", "email", "BaseHTTPServer", "httplib", "Cookie"],
    excludes=[#'_ssl',  # Exclude _ssl
              'pyreadline', 'difflib', 'doctest', 'locale',
              'pickle', 'calendar'],  # Exclude standard library
    dll_excludes=['msvcr71.dll', "w9xpopen.exe", 'mswsock.dll', 'powrprof.dll'],  # Exclude msvcr71
    compressed=True,  # Compress library.zip
    bundle_files=1,
    dist_dir=".",
    )

setup(console=["server.py"], 
        zipfile=None,
        options={'py2exe': py2exe_options},)
