# Demo project for issue with memory leak in pyarrow using parquet and pandas


## Tested Envs

```
Platform: Windows 10 Pro 22H2, WSL2 (Ubuntu 22.04.2 LTS)
HW: AMD 5600H + 32GB RAM, WSL2 has 16GB of RAM
Docker: 24.0.2, default settings, OOM killer enabled
python: 3.10.13-slim-bullseye
pyarrow==15.0.0, pandas==2.1.4
```

```
Platform: MacOS 13.6
HW: MacBook Pro M1 Max, 32GB RAM
Docker: 24.0.6 (Docker Desktop), 24GB mem limit, default settings, OOM killer enabled
python: 3.10.13-slim-bullseye
pyarrow==15.0.0, pandas==2.1.4
```


## Steps to reproduce

```
git clone https://github.com/ales-vilchytski/pyarrow-parquet-memory-leak-demo
cd pyarrow-parquet-memory-leak-demo

docker build -t memleak .
docker run --rm -it --memory=12g --memory-swap=12g memleak
```

Script runs few iterations and crashes with OOM, sometime it can run 40+ iterations.


## Example

Running in WSL2 with 16GB available RAM and 12GB limit:
```
## .wslconfig
[wsl2]
memory=16GB

## bash
$ docker run --rm -it --memory=12g --memory-swap=12g memleak
Reading data
.iteration 0, time 5.239604711532593s
...
.iteration 4, time 4.45745587348938s

$ grep oom /var/log/kern.log
[ 1016.926650] python invoked oom-killer: gfp_mask=0xcc0(GFP_KERNEL), order=0, oom_score_adj=0
[ 1016.926670]  oom_kill_process.cold+0xb/0x10
[ 1016.926715] [  pid  ]   uid  tgid total_vm      rss pgtables_bytes swapents oom_score_adj name
[ 1016.926718] oom-kill:constraint=CONSTRAINT_MEMCG,nodemask=(null),cpuset=081a665985e0314e261f773335ad0e89cb12605933c462c5d48a516a7340e560,mems_allowed=0,oom_memcg=/docker/081a665985e0314e261f773335ad0e89cb12605933c462c5d48a516a7340e560,task_memcg=/docker/081a665985e0314e261f773335ad0e89cb12605933c462c5d48a516a7340e560,task=python,pid=8730,uid=0
[ 1016.926826] Memory cgroup out of memory: Killed process 8730 (python) total-vm:48486172kB, anon-rss:12553380kB, file-rss:55616kB, shmem-rss:0kB, UID:0 pgtables:26904kB oom_score_adj:0
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

- using smaller file with smaller strings still reproduce issue with low mem limit (e.g. 40MB file with 30KB strings with 3GB mem limit)
- using smaller file seems profits from larger mem limit more, like 3GB - tens iterations, 4GB - hundreds iterations before OOM
- switching from jemalloc to malloc makes things worse
- script fails after few dozens iterations, much larger heap/swap size allows script to run significantly longer
- we encounter OOM on production in k8s, pod has memory limit of 24GB and usually fails to process 100+ files of around 200MB each
- tried `pyarrow 13, 14`, `pandas 2.0.3`, images `python bullseye` and `bookworm` - no effect
- Mac uses more memory, but AFAIK it's expected behaviour, so 12GB memory limit ends with few iterations before OOM


## Workarounds

No full workarounds found, but some tweaks can help in some cases

### Explicitly set 'string' type for columns

Setting strings type as `astype('string')` makes OOM much harder to encounter

To reproduce it, use build arg '--use-strings':
```
$ docker build -t memleak-str --build-arg="GENERATOR_ARGS=--use-strings" .
$ docker run --rm -it --memory=12g --memory-swap=12g memleak-str
```

If you check dataframe right before writing to parquet, it shows as following:
```
# Default
Index: 200000 entries, 0 to 199999
Data columns (total 1 columns):
 #   Column  Non-Null Count   Dtype
---  ------  --------------   -----
 0   s1      200000 non-null  object
dtypes: object(1)
memory usage: 3.1+ MB

# --use-strings
Index: 200000 entries, 0 to 199999
Data columns (total 1 columns):
 #   Column  Non-Null Count   Dtype
---  ------  --------------   -----
 0   s1      200000 non-null  string
dtypes: string(1)
memory usage: 3.1 MB
```

### Use python 3.12 and/or jemalloc settings

Python 3.12 and some jemalloc opts tuning may work better but also it may affect performance.

As example `docker run --rm -it --memory=12g --memory-swap=12g --env="JE_ARROW_MALLOC_CONF=abort_conf:true,confirm_conf:true,retain:false,background_thread:true,dirty_decay_ms:0,muzzy_decay_ms:0,lg_extent_max_active_fit:2" memleak` seems to work more stable but still performant.
