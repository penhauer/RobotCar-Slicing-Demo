# bind 8881 of remote to localhost:8888 where the jupyter notebook is running
ssh -R localhost:8888:localhost:8888 hpc1 -N
