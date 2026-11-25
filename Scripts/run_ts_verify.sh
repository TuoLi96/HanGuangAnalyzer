#!/bin/bash

mkdir -p $HG_WORK_ROOT/log
echo "============================" >> $HG_WORK_ROOT/log/verify_ts.log
PYTHONUNBUFFERED=1 hg-verify-ts | tee -a $HG_WORK_ROOT/log/verify_ts.log
