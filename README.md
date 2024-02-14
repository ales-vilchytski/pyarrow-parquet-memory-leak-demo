# Demo project for issue with memory leak in pyarrow using parquet and pandas


## Tested Envs

```
Platform: Windows 10 Pro 22H2, WSL2 (Ubuntu 22.04.2 LTS)
HW: AMD 5600H + 32GB RAM, WSL2 has 6-12GB of RAM
Docker: 24.0.2, default settings, OOM killer enabled
python: 3.10.13-slim-bullseye
pyarrow==15.0.0, pandas==2.1.4
```

```
Platform: MacOS 13.6
HW: MacBook Pro M1 Max, 32GB RAM
Docker: 24.0.6 (Docker Desktop), default settings, OOM killer enabled
python: 3.10.13-slim-bullseye
pyarrow==15.0.0, pandas==2.1.4
```

## Steps to reproduce

```
git clone https://github.com/ales-vilchytski/pyarrow-parquet-memory-leak-demo
cd pyarrow-parquet-memory-leak-demo

docker build -t memleak .
docker run --rm -it --memory=3g --memory-swap=3g memleak
```


## Example

Running in WSL2 with 12GB available RAM:
```
## .wslconfig
[wsl2]
memory=12GB

## bash
$ docker run --rm -it --memory=3g --memory-swap=3g memleak
.Reading data
iteration 0, time 0.629417896270752s
...
iteration 13, time 0.5989785194396973s

$ grep /var/log/kern.log oom
Memory cgroup out of memory: Killed process 20353 (python) total-vm:11536868kB, anon-rss:3129832kB, file-rss:60396kB, shmem-rss:0kB, UID:0 pgtables:12616kB oom_score_adj:0
```

If set 4G as container memory limit:
```
$ docker run --rm -it --memory=4g --memory-swap=4g memleak
.Reading data
iteration 0, time 0.6566565036773682s
...
iteration 149, time 0.5674726963043213s

$ grep /var/log/kern.log oom
Memory cgroup out of memory: Killed process 20746 (python) total-vm:14599652kB, anon-rss:4175264kB, file-rss:60404kB, shmem-rss:0kB, UID:0 pgtables:17152kB oom_score_adj:0
```


## Behaviour

Core code is following:
```
data = ds.dataset('../data/example.parquet')  # parquet file 150+MB
df = data.to_table().to_pandas()
```
This code allocates memory which is not fully freed until exit. 
So iterating over many files exhaust available memory and causes OOM eventually.

- switching from jemalloc to malloc makes things even worse
- script fails after few dozens iterations, larger heap/swap size allows script to run significantly longer
- we encounter OOM on production in k8s, pod has memory limit of 24GB and usually fails to process 100+ files of around 200MB each
- python 3.12 and some jemalloc opts tuning may work better but still encounters OOM
- as example `docker run --rm -it --memory=3g --memory-swap=3g --env="JE_ARROW_MALLOC_CONF=abort_conf:true,confirm_conf
:true,retain:false,background_thread:true,dirty_decay_ms:0,muzzy_decay_ms:0,lg_extent_max_active_fit:2" memleak` seems to work much longer before OOM
- tried `pyarrow 13, 14`, `pandas 2.0.3`, images `python bullseye` and `bookworm` - no effect
- Mac uses more memory, but AFAIK it's expected behaviour, so 6GB memory limit ends with 40+ iterations
