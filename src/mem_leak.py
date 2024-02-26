import argparse

import sys
import pyarrow as pa
import pyarrow.dataset as ds
from pathlib import Path
import time
import signal
import time


def main(args):
    print("Reading data")
    pa.log_memory_allocations(enable=args.log_memory_allocations)

    c = 0
    while True:
        start = time.time()
        data = ds.dataset('../data/example.parquet')
        df = data.to_table().to_pandas()

        pa.Table.from_pandas(df)
        
        end = time.time()
        print(f'.iteration {c}, time {end - start}s')
        c += 1
        if args.sleep_each_iteration >= 0:
            time.sleep(args.sleep_each_iteration)


def interrupt_handler(signum, frame):
    print('interrupted')
    sys.exit(0)

if __name__ == '__main__':
    signal.signal(signal.SIGINT, interrupt_handler)

    parser = argparse.ArgumentParser("Iterate over singe parquet file and do to_table.to_pandas")
    parser.add_argument('--log-memory-allocations', action='store_true')
    parser.add_argument('--sleep-each-iteration', type=int, default=-1)

    main(parser.parse_args())
