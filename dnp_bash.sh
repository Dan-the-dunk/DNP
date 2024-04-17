#!/bin/bash
echo Start the thing 


source /home/k66/miniconda3/etc/profile.d/conda.sh
conda activate dnk_dnp_env


# Define list of session names and corresponding Python programs
sessions=("sessionBbox" "sessionPose" "sessionResults")
programs=("getBoundingBox.py" "getPose.py" "saveResults.py" )


tmux new-session -d -s "docker_dnp"
tmux send-keys -t "docker_dnp":0 'docker-compose up' C-m 
echo "Started session Docker DNP"

sleep 10

# Loop through each session and program
for (( i=0; i<${#sessions[@]}; i++ )); do
  tmux new-session -d -s "${sessions[i]}" \; \
  send-keys "conda activate dnk_dnp_env; python ${programs[i]} && read" C-m
  echo "Started session ${sessions[i]} with program ${programs[i]}"

done

sleep 5

tmux new-session -d -s "sessionVideo"
tmux send-keys "conda activate dnk_dnp_env; python readVideo.py && read" C-m
echo "Started session Video with program readVideo.py"

# Attach to the first session by default (optional)
tmux attach -t "${sessions[0]}"