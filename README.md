# zillow-public-data
A simple repo which downloads Zillow's public data (no API access required!) and provides some naïve visualization

# Why?
As a first time home buyer data was an important factor for me. Getting Zillow's data was not too hard, but getting it all was a bit teadious. The juypter notebook `download.ipynb` is an attempt to automate the download process. Zillow updates their data monthly and for more details (or manual downloads) you can take a look [here](https://www.zillow.com/research/data/). Some vizualization how-to examples are provided in `viz.ipynb`. 

![City_invt_fs_uc_sfr_month.csv.png](./City_invt_fs_uc_sfr_month.csv.png)
![County_mean_doz_pending_uc_sfrcondo_sm_month.csv.png](./County_mean_doz_pending_uc_sfrcondo_sm_month.csv.png)
![Metro_median_sale_price_uc_sfrcondo_sm_month.csv.png](./Metro_median_sale_price_uc_sfrcondo_sm_month.csv.png)
![Neighborhood_zhvi_uc_sfrcondo_tier_0.67_1.0_sm_sa_month.csv.png](./Neighborhood_zhvi_uc_sfrcondo_tier_0.67_1.0_sm_sa_month.csv.png)
![State_mean_sale_price_uc_sfrcondo_month.csv.png](./State_mean_sale_price_uc_sfrcondo_month.csv.png)
# Note
The script checks all endpoints against all geography selections. As a result, there is expected that many downloads will fail as the endpoint does not support the geography.
