#!/bin/bash
#SBATCH --job-name=agentic-ai-tests
#SBATCH --output=slurm_logs/%x_%j.out
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --time=00:10:00
#SBATCH --mem-per-cpu=1G

# --- Handle runtime arguments ---
if [ -z "$1" ]; then
  echo "Usage: sbatch job.sbatch <run_name>"
  exit 1
fi

RUN_NAME=$1
DATE=$(date +%Y-%m-%d)

echo "Running tests for run name: $RUN_NAME on $DATE"

module load python/3.10
module load podman
module load rust # Required to build podman-py python package in `pip install`

source .venv/bin/activate
# Check if the virtual environment is activated
if [ -z "$VIRTUAL_ENV" ]; then
  echo "Virtual environment is not activated. Please activate it before running this script."
  exit 1
fi
pip install --no-index --upgrade pip
pip install --no-index -r requirements.txt
pytest