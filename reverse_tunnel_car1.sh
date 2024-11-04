# bind 8881 of remote to localhost:8888 where the jupyter notebook is running
ssh -R localhost:8881:localhost:8888 amirmo@129.97.168.82 -N
