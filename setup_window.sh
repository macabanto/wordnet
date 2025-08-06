#!/bin/bash

SESSION="five_panes"

# Kill existing session if it exists
tmux has-session -t $SESSION 2>/dev/null
if [ $? -eq 0 ]; then
  tmux kill-session -t $SESSION
fi

# Start new session (pane 0 is full window initially)
tmux new-session -d -s $SESSION

# Focus top pane (pane 0), then split it into 5 horizontal panes
tmux select-pane -t $SESSION:0.0
tmux split-window -h
tmux split-window -h
tmux split-window -h
tmux split-window -h

# Evenly distribute the top row horizontally
tmux select-layout -t $SESSION even-horizontal

# Run log watchers in each top pane
tmux send-keys -t $SESSION:0.0 'docker logs -f scraper-system-scraper_worker_0-1' C-m
tmux send-keys -t $SESSION:0.1 'docker logs -f scraper-system-scraper_worker_1-1' C-m
tmux send-keys -t $SESSION:0.2 'docker logs -f scraper-system-scraper_worker_2-1' C-m
tmux send-keys -t $SESSION:0.3 'docker logs -f scraper-system-scraper_worker_3-1' C-m
tmux send-keys -t $SESSION:0.4 'docker logs -f scraper-system-scraper_worker_4-1' C-m

# Bottom pane (pane 5) spans the width of terminal
tmux send-keys -t $SESSION:0.5 'watch -n 2 "docker stats --no-stream && echo && docker ps -a"' C-m

# Attach to session
tmux attach-session -t $SESSION