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

# Windows 10 WSL2
docker run --rm -it --memory=3g --memory-swap=3g memleak

# MacOS ARM
docker run --rm -it --memory=4.5g --memory-swap=4.5g memleak
```

Script runs few iterations and crashes with OOM, sometime it can run 40+ iterations.


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
.iteration 4, time 0.777557373046875s

$ grep oom /var/log/kern.log
[23135.515654] python invoked oom-killer: gfp_mask=0xcc0(GFP_KERNEL), order=0, oom_score_adj=0
[23135.515675]  oom_kill_process.cold+0xb/0x10
[23135.515728] [  pid  ]   uid  tgid total_vm      rss pgtables_bytes swapents oom_score_adj name
[23135.515731] oom-kill:constraint=CONSTRAINT_MEMCG,nodemask=(null),cpuset=d373ef1358ecbc4b7f1b8cb5324fb303dd19d0371bb541cb9cdff4c30e58f572,mems_allowed=0,oom_memcg=/docker/d373ef1358ecbc4b7f1b8cb5324fb303dd19d0371bb541cb9cdff4c30e58f572,task_memcg=/docker/d373ef1358ecbc4b7f1b8cb5324fb303dd19d0371bb541cb9cdff4c30e58f572,task=python,pid=143087,uid=0
[23135.515844] Memory cgroup out of memory: Killed process 143087 (python) total-vm:9650240kB, anon-rss:3131008kB, file-rss:56384kB, shmem-rss:0kB, UID:0 pgtables:12088kB oom_score_adj:0
```

If set 4G as container memory limit:
```
$ docker run --rm -it --memory=4g --memory-swap=4g memleak
.Reading data
iteration 0, time 0.6566565036773682s
...
.iteration 34, time 0.4770951271057129s

$ grep oom /var/log/kern.log
[23049.672539] python invoked oom-killer: gfp_mask=0xcc0(GFP_KERNEL), order=0, oom_score_adj=0
[23049.672560]  oom_kill_process.cold+0xb/0x10
[23049.672604] [  pid  ]   uid  tgid total_vm      rss pgtables_bytes swapents oom_score_adj name
[23049.672607] oom-kill:constraint=CONSTRAINT_MEMCG,nodemask=(null),cpuset=a52bc20803865afedd66f9293e90114e30a7d2196f95c678aa701e11d8f40a79,mems_allowed=0,oom_memcg=/docker/a52bc20803865afedd66f9293e90114e30a7d2196f95c678aa701e11d8f40a79,task_memcg=/docker/a52bc20803865afedd66f9293e90114e30a7d2196f95c678aa701e11d8f40a79,task=python,pid=141389,uid=0
[23049.672711] Memory cgroup out of memory: Killed process 141389 (python) total-vm:11825220kB, anon-rss:4179972kB, file-rss:56256kB, shmem-rss:0kB, UID:0 pgtables:11564kB oom_score_adj:0
```


## Other observations

Core code is following:
```
data = ds.dataset('../data/example.parquet')  # parquet file with many long strings
while True:
    df = data.to_table().to_pandas()
```
This code allocates memory which is not fully freed until exit. 
So iterating over many files or many times over same file exhaust available memory and causes OOM eventually.

- switching from jemalloc to malloc makes things even worse
- script fails after few dozens iterations, larger heap/swap size allows script to run significantly longer
- we encounter OOM on production in k8s, pod has memory limit of 24GB and usually fails to process 100+ files of around 200MB each
- tried `pyarrow 13, 14`, `pandas 2.0.3`, images `python bullseye` and `bookworm` - no effect
- Mac uses more memory, but AFAIK it's expected behaviour, so 6GB memory limit ends with few hundred iterations before OOM


## Workarounds

No full workarounds found, but some tweaks can help in some cases

### Explicitly set 'string' type for columns

Setting strings type as `astype('string')` makes OOM much harder to encounter

To reproduce it, use build arg '--use-strings':
```
$ docker build -t no-memleak --build-arg="GENERATOR_ARGS=--use-strings" .
$ docker run --rm -it --memory=3g --memory-swap=3g no-memleak
```

If you check dataframe right before writing to parquet, it shows as following:
```
# Default
Index: 100000 entries, 0 to 99999
Data columns (total 2 columns):
 #   Column  Non-Null Count   Dtype
---  ------  --------------   -----
 0   s1      100000 non-null  object
 1   s2      100000 non-null  object
dtypes: object(2)
memory usage: 2.3+ MB

# --use-strings
Index: 100000 entries, 0 to 99999
Data columns (total 2 columns):
 #   Column  Non-Null Count   Dtype
---  ------  --------------   -----
 0   s1      100000 non-null  string
 1   s2      100000 non-null  string
dtypes: string(2)
memory usage: 2.3 MB
```

### Use python 3.12 and/or jemalloc settings

Python 3.12 and some jemalloc opts tuning may work better but also it may affect performance.

As example `docker run --rm -it --memory=3g --memory-swap=3g --env="JE_ARROW_MALLOC_CONF=abort_conf:true,confirm_conf:true,retain:false,background_thread:true,dirty_decay_ms:0,muzzy_decay_ms:0,lg_extent_max_active_fit:2" memleak` seems to work more stable but still performant.
