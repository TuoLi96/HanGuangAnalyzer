#!/bin/bash

set -euo pipefail                                                               
                                                                                
mkdir -p $HG_WORK_ROOT/log

$HG_ROOT/Scripts/compile_linux.sh 2>&1 | tee $HG_WORK_ROOT/log/compile.log
$HG_ROOT/Scripts/build_knowledge.sh 2>&1 | tee $HG_WORK_ROOT/log/build_knowledge.log
