#!/bin/bash
echo Start the thing 


source ~miniconda3/etc/profile.d/conda.sh
conda activate dnk_dnp_env


# Define list of session names and corresponding Python programs
sessions=( "sessionVideo" "sessionBbox" "sessionPose" "sessionResults")
programs=( "readVideo.py" "getBoundingBox.py" "getPose.py" "saveResults.py" )

for (( i=0; i<${#sessions[@]}; i++ )); do
  echo "${sessions[i]}"
  echo "${programs[i]}"
done