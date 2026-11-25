#!/bin/bash

mkdir -p $HG_WORK_ROOT/log

$HG_ROOT/Scripts/prepare.sh
echo "==========================" >> $HG_WORK_ROOT/log/ts_analysis.log
PYTHONUNBUFFERED=1 hg-ts-analysis 2>&1 | tee -a $HG_WORK_ROOT/log/ts_analysis.log
hg-collect-ts-tasks
