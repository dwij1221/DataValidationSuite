import pandas as pd
import numpy as np
from datetime import datetime
import os

# make sure raw folder exists
os.makedirs("../data/raw", exist_ok=True)

n_days = 90
dates = pd.date_range(end=pd.Timestamp.today(), periods=n_days, freq="D")
stores = [f"S{i:03d}" for i in range(1, 6)]
skus = [f"SKU{1000+i}" for i in range(200)]

rows = []
for d in dates:
    for s in stores:
        for _ in range(np.random.poisson(5) + 1):
            sku = np.random.choice(skus)
            units = max(1, int(np.random.poisson(2)))
            price = round(np.random.uniform(10, 500), 2)
            revenue = round(units * price, 2)
            promo = int(np.random.rand() < 0.1)

            # inject some bad data occasionally
            if np.random.rand() < 0.005:
                revenue = -abs(revenue)

            rows.append([d.date().isoformat(), s, sku, units, price, revenue, promo])

df = pd.DataFrame(rows, columns=["date","store_id","sku","units_sold","price","revenue","promo_flag"])

out_file = f"../data/raw/retail_sample_{datetime.now().strftime('%Y%m%d')}.csv"
df.to_csv(out_file, index=False)

print("Sample data written to:", out_file)
