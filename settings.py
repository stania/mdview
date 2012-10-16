import json
import os


class Settings(object):
    RES_PATH = ".res"

    @classmethod
    def __set_default_settings(self, dct):
        if not dct.has_key("base_dir"):
            dct["base_dir"] = os.path.join(dct["base_dir"], self.RES_PATH)
        if not dct.has_key("res_dir"):
            dct["res_dir"] = os.path.join(dct["base_dir"], self.RES_PATH)
        if not dct.has_key("server_port"):
            dct["server_port"] = 7559
        if not dct.has_key("debug"):
            dct["debug"] = False
        if not dct.has_key("md_exts"):
            dct["md_exts"] = [".md"]
        return dct

    def __init__(self, json_path):
        dct = {}
        if os.path.exists("mdview.cfg"):
            print "loading settings from", os.path.abspath("mdview.cfg")
            dct = self.__set_default_settings(json.load(open("mdview.cfg")))
        else:
            dct = self.__set_default_settings({
                "base_dir": os.getcwd(),
                "res_dir": os.path.join(os.getcwd(), self.RES_PATH),
                "debug" : False,
            })
        for k, v in dct.iteritems():
            setattr(self, k, v)
        
def load_settings():
    return Settings("mdview.cfg")


def main():
    settings = load_settings()
    for k, v in vars(settings).iteritems():
        print k, v

if __name__ == "__main__":
    main()


