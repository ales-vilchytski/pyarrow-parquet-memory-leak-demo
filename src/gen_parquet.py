import argparse

import pyarrow.parquet as pq
import pandas as pd
import pyarrow as pa

def main(args):
    idx = []
    data = {
        's1': [],
        's2': [],
    }
    c = 0

    print('generating')
    for i in range(100000):
        data['s1'].append(f'abc{c}'*300)
        data['s2'].append(f'def{c}'*300)
        c = c + 1
        idx.append(i)


    df = pd.DataFrame(data, index=idx)
    if args.use_strings:
        df = df.astype({'s1': 'string', 's2': 'string'})

    print('writing')
    table = pa.Table.from_pandas(df)
    print(table.schema)
    df.info()
    pq.write_table(table, '../data/example.parquet')
    print("done")


if __name__ == '__main__':
    parser = argparse.ArgumentParser("Generate parquet file from pandas dataframe with long strings")
    parser.add_argument('--use-strings', action='store_true')
    main(parser.parse_args())
