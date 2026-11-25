#!/usr/bin/env python3 

import sys
from HG.Knowledge.SymMgr import SymMgr

def main(args):
    sym_mgr = SymMgr()
    src_file = args[0]
    func_name = args[1]
    print(sym_mgr.get_func_def(src_file, func_name))

if __name__ == "__main__":
    main(sys.argv[1:])
