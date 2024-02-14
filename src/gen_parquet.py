import pyarrow.parquet as pq
import pandas as pd
import pyarrow as pa

idx = []
data = {
    'a': [],
    'b': [],
    'c': [],
}
a = 0.0
b = 0
c = 0

print('generating')
for i in range(100000):
    a = a + 0.1
    data['a'].append(a)
    b = b + 1
    data['b'].append('abc'*100 + str(b))
    c = c + 1
    data['c'].append('def'*1000 + str(c))
    idx.append(i)


df = pd.DataFrame(data, index=idx)
df = df.astype({'a': 'float64','b': 'string','c': 'string'})

print('writing')
table = pa.Table.from_pandas(df)
pq.write_table(table, '../data/example.parquet')
print("done")
