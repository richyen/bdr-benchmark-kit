#!/bin/bash
set -e
set -x

if [[ ${1} == '' ]]; then
  echo "Usage: ${0} <project_dir>"
  exit 1
fi

# Where the scripts and config live
PROJ_DIR="${HOME}/code/edb/bdr-benchmark-kit"

# Where we want to deploy our cluster
WORK_DIR=${1}

# Create Terraform cluster dir
python ${PROJ_DIR}/scripts/new-project.py ${WORK_DIR} ${PROJ_DIR}/gold-infrastructure.yml        

# Initialize Terraform cluster
terraform -chdir=${WORK_DIR} init

# Apply Terraform cluster
terraform -chdir=${WORK_DIR} apply -auto-approve

# Create tpaexec deploy script
python ${PROJ_DIR}/scripts/pre-deploy.py -a gold ${WORK_DIR} ${PROJ_DIR}/configuration.yml           

# Deploy with tpaexec
${WORK_DIR}/deploy.sh
