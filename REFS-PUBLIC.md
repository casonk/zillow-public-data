# REFS-PUBLIC.md - Public References

> Record external public repositories, datasets, documentation, APIs, or other
> public resources that this repository utilizes or depends on.
> This file is tracked and intentionally kept free of private or local-only details.

## Public Repositories

- No fixed external code repository is the main upstream; the repo mirrors Zillow public data feeds.

## Public Datasets and APIs

- https://www.zillow.com/research/data/ - source directory for Zillow public CSV feeds
- https://files.zillowstatic.com/research/public_csvs/ - primary public CSV download base used by `refresh.py`
- https://files.zillowstatic.com/research/public_v2/ - alternate public-data download base used by `refresh.py`
- https://www.zillowgroup.com/developers/api/public-data/real-estate-metrics/ - Zillow public-data program reference

## Documentation and Specifications

- https://www.zillow.com/research/market-heat-index-methodology-31867/ - market heat index methodology reference
- https://www.zillow.com/research/methodology-neural-zhvi-32128/ - Zillow Home Value Index methodology reference
- https://www.zillow.com/research/zori-repeat-rent-methodology-27092/ - Zillow Observed Rent Index methodology reference
- https://www.zillow.com/z/corp/terms/ - Zillow public-data terms of use
- https://pandas.pydata.org/docs/ - pandas CSV and tabular-data processing reference used by refresh and example generation
- https://requests.readthedocs.io/ - Requests HTTP client reference used by Zillow CSV fetch paths

## Notes

- The repo mirrors public CSV feeds locally rather than calling a private API. Methodology pages belong here because they explain the meaning of tracked columns and indices.
