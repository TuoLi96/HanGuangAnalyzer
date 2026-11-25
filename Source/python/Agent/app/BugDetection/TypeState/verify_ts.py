#!/usr/bin/env python3 

from HG.Agent.Base.Chat import ChaterMgr
from HG.Agent.BugDetection.TypeState import TSAgentMgr

import sys
import json
import threading

from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

def process_task(index, task, ts_agent_mgr):
    max_rounds = ts_agent_mgr.get_max_tool_rounds()
    try:
        bug_desp = task["desp"]
        chater_mgr = ChaterMgr()
        chater = chater_mgr.get_chater(index, ts_agent_mgr)
        task_prompt = ts_agent_mgr.get_task_prompt()
        task_info = (f"{task_prompt}\n{bug_desp}")
        chater.add_user(task_info)
        if not chater.chat_with_tools(max_rounds):
            return False
        chater.save_token_usage()
        ts_agent_mgr.done(index)
        token_usage = chater.get_token_usage(
                    chater_mgr.get_in_cost(), 
                    chater_mgr.get_cached_in_cost(),
                    chater_mgr.get_out_cost())
        tqdm.write(f"[{index}] {token_usage}", file=sys.stdout)
        return True
    except Exception as e:
        tqdm.write(f"[{index}] failed: {e}")
        return False

def main():
    ts_agent_mgr = TSAgentMgr()
    workers = ts_agent_mgr.get_num_threads()
    batch_size = ts_agent_mgr.get_batch_size()
    tasks = ts_agent_mgr.get_tasks()
    pending = [
        i for i in range(len(tasks))
        if not ts_agent_mgr.is_done(i)
    ]
    #pending = [2820, 2921, 3190, 5768, 6176, 6196, 6298, 7603, 7698, 7875, 8340, 8494, 8725, 9135, 9351]
    success_cnt = 0
    progress = tqdm(total=len(pending), desc="TS Verify")

    with ThreadPoolExecutor(max_workers=workers) as executor:
        for start in range(0, len(pending), batch_size):
            batch = pending[start:start + batch_size]
            futures = []
            tqdm.write(f"Submit batch {start}-{start+len(batch)}")
            for i in batch:
                future = executor.submit(
                    process_task,
                    i,
                    tasks[i],
                    ts_agent_mgr
                )
                futures.append(future)
            for future in as_completed(futures):
                try:
                    if future.result():
                        success_cnt += 1
                except Exception as e:
                    tqdm.write(f"Worker exception: {e}")
                finally:
                    progress.update(1)
            tqdm.write(f"Batch finished, success={success_cnt}")
    progress.close()
    ts_agent_mgr.save_checkpoint()

if __name__ == "__main__":
    main()
