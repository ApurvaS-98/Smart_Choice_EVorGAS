# EV vs Gas Cost Analysis

A Streamlit web application that compares the commuting costs between electric vehicles (EV) and gas vehicles based on your daily commute.

## Features

- Calculate commute distance using home and work addresses
- Find nearest EV charging stations
- Compare EV vs gas vehicle costs (monthly and yearly)
- Interactive visualizations showing cost comparisons and potential savings
- Support for multiple EV models and gas types

## Data Sources

- `ev_specs.csv` - Electric vehicle specifications (battery capacity, range)
- `ev_prices.csv` - Electricity costs per kWh by state
- `gas_prices.csv` - Gas prices by state (Regular, Mid-grade, Premium)
- `fuel_stations_cleaned.csv` - EV charging station locations

## Requirements

- Python 3.x
- streamlit
- pandas
- altair
- geopy
- openrouteservice

## Usage

```bash
streamlit run app.py
```

Enter your home and work addresses, select an EV model, and optionally compare against a gas vehicle to see potential savings.
