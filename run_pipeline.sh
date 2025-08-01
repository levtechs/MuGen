#THIS FILE CRASHES! Do NOT run!!!

#!/bin/sh

# ==============================================================================
# DATASET PROCESSING PIPELINE - ORCHESTRATOR (V3 - Safe Parallelism & Memory Limit)
# ==============================================================================

# --- Configuration ---
VENV_PATH="venv"
INPUT_DIR="./clean_midi"
OUTPUT_DIR="./outputs"
MAX_JOBS=4 # Number of parallel jobs

# --- MEMORY SAFETY LIMIT ---
# Max memory PER PROCESS in kilobytes (KB).
# 4GB = 4 * 1024 * 1024 = 4194304 KB
# Set this to a safe value below your available RAM.
# For example, if you have 16GB free, 4GB per process is safe for 4 jobs.
MEMORY_LIMIT_KB=4194304

# --- Script Logic ---
set -eu

TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
MASTER_LOG_FILE="${OUTPUT_DIR}/processing_log_${TIMESTAMP}.log"

PYTHON_EXEC="$VENV_PATH/bin/python3"
if [ ! -x "$PYTHON_EXEC" ]; then
    echo "❌ Error: Python executable not found at '$PYTHON_EXEC'" >&2
    exit 1
fi

mkdir -p "$OUTPUT_DIR"
echo "Pipeline started at $(date)" > "$MASTER_LOG_FILE"
echo "✅ Output will be saved to: $OUTPUT_DIR"
echo "✅ All detailed logs will be appended to: $MASTER_LOG_FILE"
echo "✅ Parallel jobs limited to: $MAX_JOBS"
echo "✅ Memory limit per job set to: $((MEMORY_LIMIT_KB / 1024)) MB"

# --- THIS IS THE MEMORY-SAFE SOLUTION ---
TOTAL_ARTISTS=$(find "$INPUT_DIR" -mindepth 1 -maxdepth 1 -type d | wc -l | xargs)

echo "Found $TOTAL_ARTISTS artists to process..."
echo "---"

PROCESSED_COUNT=0

find "$INPUT_DIR" -mindepth 1 -maxdepth 1 -type d | while read -r artist_path; do
    # --- CORRECT PARALLELISM CONTROL ---
    # (The rest of your loop body goes here, unchanged)
    while [ $(jobs -p | wc -l) -ge "$MAX_JOBS" ]; do
        echo "Number of jobs: $(jobs -p | wc -l)"
        wait
    done

    # Now that we know there's a free slot, launch the next job.
    PROCESSED_COUNT=$((PROCESSED_COUNT + 1))
    artist_name=$(basename "$artist_path")
    output_pt_file="$OUTPUT_DIR/${artist_name}.pt"

    if [ -f "$output_pt_file" ]; then
        echo "[$PROCESSED_COUNT/$TOTAL_ARTISTS] ⏭️  SKIPPING: ${artist_name} (output already exists)"
        continue
    fi

    # Launch job in the background within a subshell
    (
        echo "[$PROCESSED_COUNT/$TOTAL_ARTISTS] 🚀 STARTING: ${artist_name}"
        ulimit -v $MEMORY_LIMIT_KB
        LOG_FILE="${OUTPUT_DIR}/artist-${artist_name}.log"
        "$PYTHON_EXEC" process_artist.py --artist-dir "$artist_path" --output-file "$output_pt_file" >> "$LOG_FILE" 2>&1
        if [ $? -eq 0 ]; then
            echo "[$PROCESSED_COUNT/$TOTAL_ARTISTS] ✅ FINISHED: ${artist_name}"
        else
            echo "[$PROCESSED_COUNT/$TOTAL_ARTISTS] ❌ FAILED: ${artist_name}. Check log for details (may be due to memory limit)."
        fi
    ) &
done

# Wait for all remaining background jobs to complete before exiting
echo "---"
echo "Waiting for the last batch of jobs to finish..."
wait
echo "All jobs complete."

echo "---" >> "$MASTER_LOG_FILE"
echo "Pipeline finished at $(date)" >> "$MASTER_LOG_FILE"
echo "🎉 All artists processed!"
echo "✅ Dataset generated in $OUTPUT_DIR"