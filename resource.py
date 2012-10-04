import glob, sys, imp

res_list = []

def main_is_frozen():
    return (hasattr(sys, "frozen") or
            hasattr(sys, "importers") or
            imp.is_frozen("__main__"))

if main_is_frozen():
    __import__("_reslist")
    res_list = getattr(sys.modules["_reslist"], "_res")
    res_list.sort()
else:
    res_list = glob.glob(".res/*.*")
    res_list.sort()

def res_id_dict():
    R = {}
    for r, i in zip(res_list, xrange(1, len(res_list) + 1)):
        R[r] = i
    return R

def py2exe_list():
    R = []
    print res_list
    for r, i in zip(res_list, xrange(1, len(res_list) + 1)):
        R.append((u'RESOURCE', i, open(r).read()))
    return R

def gen_reslist_py():
    reslist_content = repr(res_id_dict().keys())
    open("_reslist.py", "w").write("""_res = {}""".format(reslist_content))
