#!/bin/bash

set -e

export KBUILD_ABS_SRCTREE=1
export KBUILD_ABS_OBJDIR=1

cd "$HG_CHECKED_SRC"

HG_COMPILE="$HG_FRONTEND/Compile"

make clean
make mrproper

yes "" | PATH="$HG_COMPILE:$PATH" make LLVM=1 allyesconfig

scripts/config --disable KASAN
scripts/config --disable KASAN_GENERIC
scripts/config --disable KASAN_SW_TAGS
scripts/config --disable KASAN_HW_TAGS

scripts/config --disable KCOV
scripts/config --disable UBSAN
scripts/config --disable KCSAN
scripts/config --disable GCOV_KERNEL

scripts/config --disable FTRACE
scripts/config --disable FUNCTION_TRACER
scripts/config --disable FUNCTION_GRAPH_TRACER

scripts/config --disable TRACING
scripts/config --disable TRACEPOINTS

scripts/config --disable KPROBES
scripts/config --disable UPROBES

scripts/config --disable BPF
scripts/config --disable BPF_SYSCALL

scripts/config --disable PERF_EVENTS
scripts/config --disable PROFILING

scripts/config --disable DEBUG_KERNEL

scripts/config --disable WERROR

make LLVM=1 olddefconfig

export PATH="$HG_COMPILE:$PATH"
export HG_TARGET_MACROS="kmalloc,kzalloc,kcalloc,kmalloc_array,vmalloc,vzalloc,vmalloc_array,kmem_cache_alloc,alloc_pages,dma_alloc_coherent"

yes "" | make LLVM=1 -j"$(nproc)"

hg-close-include

make xmldocs
