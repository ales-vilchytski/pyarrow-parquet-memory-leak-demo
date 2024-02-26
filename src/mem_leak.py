import sys
import pyarrow as pa
import pyarrow.dataset as ds
from pathlib import Path
import time
import signal
import time


def main():
    print("Reading data")

    c = 0
    while True:
        start = time.time()
        data = ds.dataset('../data/example.parquet')
        df = data.to_table().to_pandas()

        pa.Table.from_pandas(df)
        
        end = time.time()
        print(f'.iteration {c}, time {end - start}s')
        c += 1
        time.sleep(0)
    

def interrupt_handler(signum, frame):
    print('interrupted')
    sys.exit(0)

if __name__ == '__main__':
    signal.signal(signal.SIGINT, interrupt_handler)

    main()
