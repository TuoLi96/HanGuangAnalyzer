#!/usr/bin/env python3 

import sys
from HG.Knowledge.SymMgr import SymMgr

def main(args):
    sym_mgr = SymMgr()
    src_file = args[0]
    struct_name = args[1]
    print(sym_mgr.get_struct_def(src_file, struct_name))

if __name__ == "__main__":
    main(sys.argv[1:])
