# HanGuang

HanGuang is an extensible program analysis harness for automated Linux kernel bug detection, integrating static analysis, typestate analysis, multi-dimensional kernel knowledge, and LLM-based verification.

```text
                 *
                ***
               *****
                ***
                ***
                ***
                ***
                ***
                ***
                ***
                ***
                ***
                ***
                ***
                ***
                ***
                ***
               *****
            ***********
          ***************
              *******
                ***
                ***
                ***
               *****
              *******
               *****
                ***
              *******
```

## Bug Detection

### 1. Configure the API Key

Set your DeepSeek API key on the host:

```bash
export DS_API_KEY="api-key"
```

### 2. Prepare the Working Directory

On the host machine:

1. Create a working directory named `workdir`.
2. Download and extract the Linux kernel source code.
3. Place the extracted kernel source code in `workdir/linux`.

### 3. Start the Docker Container

Enter the `Docker` directory and run `run_docker.sh`.

The script is as follows:

```bash
#!/bin/bash
set -e

BASE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
WORK_DIR="$BASE_DIR/workdir"

mkdir -p "$WORK_DIR"

docker pull tuoli96/hanguang:v1

docker run -it --rm \
    -e HOST_UID="$(id -u)" \
    -e HOST_GID="$(id -g)" \
    -e DS_API_KEY \
    -v "$WORK_DIR:/workdir" \
    --network host \
    --name hanguang \
    hanguang:v1
```

The script loads the HanGuang Docker image and starts the container, mounting the host's `workdir` directory at `/workdir` inside the container.

### 4. Run Static Analysis

Inside the Docker container, compile the Linux kernel and run static analysis:

```bash
run Scripts/runall_heavy.sh
```

### 5. Run the Bug Verification Agent

After static analysis completes, run the agent to verify the reported bugs:

```bash
run Scripts/run_ts_verify.sh
```

### 6. View Bug Reports

Start the bug visualization website:

```bash
run HTML/BugConfirm/bugconfirm.sh start
```

Open the displayed address in a web browser to view and inspect the bug reports.

## Typestate Configuration

To add or configure typestate specifications:

1. Place the typestate specifications in:

   ```text
   Metadata/Analyzer/BugDetection/TSes
   ```

2. Enable the corresponding typestate specifications in `ts.json`.

3. The configured typestate analysis will run automatically when executing:

   ```bash
   run Scripts/runall_heavy.sh
   ```

## Associated Publication

This project accompanies the following research paper:

**A Typestate-Guided Agent with Multi-Dimensional Kernel Knowledge for Cost-Effective Bug Detection**

The paper presents the design and implementation of HanGuang (KernelSleuth), a typestate-guided agent that leverages multi-dimensional kernel knowledge for cost-effective Linux kernel bug detection.



