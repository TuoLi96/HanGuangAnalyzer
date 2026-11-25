#!/usr/bin/env python3 

import sys
from HG.Knowledge.SymMgr import SymMgr

def main(args):
    sym_mgr = SymMgr()
    symbol_name = args[0]
    print(sym_mgr.get_doc(symbol_name))

if __name__ == "__main__":
    main(sys.argv[1:])
