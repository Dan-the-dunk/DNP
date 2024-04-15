#!/bin/bash

# Define list of session names and corresponding Python programs
sessions=( "sessionVideo" "sessionBbox" "sessionPose" "sessionResults")
programs=( "readVideo.py" "getBoundingBox.py" "getPose.py" "saveResults.py" )

# Loop through each session and program
for (( i=0; i<${#sessions[@]}; i++ )); do
  tmux new-session -d -s "${sessions[i]}" \; \
  send-keys "python ${programs[i]} && read" C-m
done

# Attach to the first session by default (optional)
tmux attach -t "${sessions[0]}"