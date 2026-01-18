import json
import pandas as pd
import requests
from geopy.geocoders import Nominatim
from geopy.distance import geodesic

# Load API key from keys.json
with open("keys.json") as f:
    keys = json.load(f)
ORS_API_KEY = keys["ORS_API_KEY"]


def get_coordinates(home_address, work_address):
    """Get coordinates for home and work addresses using geopy."""
    geolocator = Nominatim(user_agent="ev_gas_analysis", timeout=10)

    home_location = geolocator.geocode(home_address)
    work_location = geolocator.geocode(work_address)

    home_coords = (home_location.latitude, home_location.longitude)
    work_coords = (work_location.latitude, work_location.longitude)

    return home_coords, work_coords


def closest_coordinates(home_coords, work_coords):
    """Find the 3 closest fuel stations to home and work coordinates."""
    df = pd.read_csv("fuel_stations_cleaned.csv")

    # Calculate distances from home
    home_distances = []
    for idx, row in df.iterrows():
        station_coords = (row['Latitude'], row['Longitude'])
        dist = geodesic(home_coords, station_coords).miles
        home_distances.append(dist)

    df['home_distance'] = home_distances
    df_home_sorted = df.sort_values('home_distance')

    # Get top 3 unique addresses for home
    seen_addresses = set()
    top_3_home = []
    for idx, row in df_home_sorted.iterrows():
        addr = row['Street Address']
        if addr not in seen_addresses:
            seen_addresses.add(addr)
            top_3_home.append(row)
            if len(top_3_home) == 3:
                break
    top_3_home = pd.DataFrame(top_3_home)

    # Calculate distances from work
    work_distances = []
    for idx, row in df.iterrows():
        station_coords = (row['Latitude'], row['Longitude'])
        dist = geodesic(work_coords, station_coords).miles
        work_distances.append(dist)

    df['work_distance'] = work_distances
    df_work_sorted = df.sort_values('work_distance')

    # Get top 3 unique addresses for work
    seen_addresses = set()
    top_3_work = []
    for idx, row in df_work_sorted.iterrows():
        addr = row['Street Address']
        if addr not in seen_addresses:
            seen_addresses.add(addr)
            top_3_work.append(row)
            if len(top_3_work) == 3:
                break
    top_3_work = pd.DataFrame(top_3_work)

    home_result = top_3_home[['Street Address', 'City', 'State', 'ZIP', 'Latitude', 'Longitude', 'home_distance']]
    work_result = top_3_work[['Street Address', 'City', 'State', 'ZIP', 'Latitude', 'Longitude', 'work_distance']]

    print("Top 3 closest fuel stations to Home:")
    print(home_result.to_string(index=False))
    print("\nTop 3 closest fuel stations to Work:")
    print(work_result.to_string(index=False))

    return home_result, work_result


def calculate_distance(home_coords, work_coords, top_3_home, top_3_work):
    """Calculate road distances using OpenRouteService API."""
    base_url = "https://api.openrouteservice.org/v2/directions/driving-car"
    headers = {"Authorization": ORS_API_KEY}

    # Find shortest station from home
    shortest_home_distance = float('inf')
    shortest_home_station = None

    home_lonlat = (home_coords[1], home_coords[0])

    for idx, row in top_3_home.iterrows():
        station_coords = (row['Longitude'], row['Latitude'])  # ORS uses lon, lat

        params = {
            "start": f"{home_lonlat[0]},{home_lonlat[1]}",
            "end": f"{station_coords[0]},{station_coords[1]}"
        }

        response = requests.get(base_url, headers=headers, params=params)
        data = response.json()

        distance_meters = data['features'][0]['properties']['segments'][0]['distance']
        distance_miles = distance_meters * 0.000621371

        if distance_miles < shortest_home_distance:
            shortest_home_distance = distance_miles
            shortest_home_station = {
                'Street Address': row['Street Address'],
                'City': row['City'],
                'State': row['State'],
                'ZIP': row['ZIP'],
                'distance_miles': distance_miles
            }

    # Find shortest station from work
    shortest_work_distance = float('inf')
    shortest_work_station = None

    work_lonlat = (work_coords[1], work_coords[0])

    for idx, row in top_3_work.iterrows():
        station_coords = (row['Longitude'], row['Latitude'])  # ORS uses lon, lat

        params = {
            "start": f"{work_lonlat[0]},{work_lonlat[1]}",
            "end": f"{station_coords[0]},{station_coords[1]}"
        }

        response = requests.get(base_url, headers=headers, params=params)
        data = response.json()

        distance_meters = data['features'][0]['properties']['segments'][0]['distance']
        distance_miles = distance_meters * 0.000621371

        if distance_miles < shortest_work_distance:
            shortest_work_distance = distance_miles
            shortest_work_station = {
                'Street Address': row['Street Address'],
                'City': row['City'],
                'State': row['State'],
                'ZIP': row['ZIP'],
                'distance_miles': distance_miles
            }

    # Calculate home to work distance
    params = {
        "start": f"{home_lonlat[0]},{home_lonlat[1]}",
        "end": f"{work_lonlat[0]},{work_lonlat[1]}"
    }

    response = requests.get(base_url, headers=headers, params=params)
    data = response.json()

    home_work_dist = data['features'][0]['properties']['segments'][0]['distance'] * 0.000621371

    print(f"\nClosest station to Home by road:")
    print(f"  Address: {shortest_home_station['Street Address']}")
    print(f"  City: {shortest_home_station['City']}, {shortest_home_station['State']} {shortest_home_station['ZIP']}")
    print(f"  Road distance: {shortest_home_station['distance_miles']:.2f} miles")

    print(f"\nClosest station to Work by road:")
    print(f"  Address: {shortest_work_station['Street Address']}")
    print(f"  City: {shortest_work_station['City']}, {shortest_work_station['State']} {shortest_work_station['ZIP']}")
    print(f"  Road distance: {shortest_work_station['distance_miles']:.2f} miles")

    print(f"\nHome to Work distance: {home_work_dist:.2f} miles")

    return shortest_home_station, shortest_work_station, home_work_dist


def get_ev_models():
    """Get list of EV models from ev_specs.csv."""
    ev_specs_df = pd.read_csv("ev_specs.csv")
    return ev_specs_df['Car_name'].tolist()


def analysis(home_work_dist, number_of_days, state, ev_model, gas_mileage=None, gas_type="Regular", include_gas=True):
    """Analyze cost difference between gas and electric vehicles."""
    # State abbreviation to full name mapping
    state_names = {
        'AL': 'Alabama', 'AK': 'Alaska', 'AZ': 'Arizona', 'AR': 'Arkansas',
        'CA': 'California', 'CO': 'Colorado', 'CT': 'Connecticut', 'DE': 'Delaware',
        'DC': 'District of Columbia', 'FL': 'Florida', 'GA': 'Georgia', 'HI': 'Hawaii',
        'ID': 'Idaho', 'IL': 'Illinois', 'IN': 'Indiana', 'IA': 'Iowa', 'KS': 'Kansas',
        'KY': 'Kentucky', 'LA': 'Louisiana', 'ME': 'Maine', 'MD': 'Maryland',
        'MA': 'Massachusetts', 'MI': 'Michigan', 'MN': 'Minnesota', 'MS': 'Mississippi',
        'MO': 'Missouri', 'MT': 'Montana', 'NE': 'Nebraska', 'NV': 'Nevada',
        'NH': 'New Hampshire', 'NJ': 'New Jersey', 'NM': 'New Mexico', 'NY': 'New York',
        'NC': 'North Carolina', 'ND': 'North Dakota', 'OH': 'Ohio', 'OK': 'Oklahoma',
        'OR': 'Oregon', 'PA': 'Pennsylvania', 'RI': 'Rhode Island', 'SC': 'South Carolina',
        'SD': 'South Dakota', 'TN': 'Tennessee', 'TX': 'Texas', 'UT': 'Utah',
        'VT': 'Vermont', 'VA': 'Virginia', 'WA': 'Washington', 'WV': 'West Virginia',
        'WI': 'Wisconsin', 'WY': 'Wyoming'
    }
    state_full = state_names.get(state, state)

    # Read EV specs from CSV
    ev_specs_df = pd.read_csv("ev_specs.csv")
    ev_row = ev_specs_df[ev_specs_df['Car_name'] == ev_model].iloc[0]
    battery_capacity = float(ev_row['Battery'])
    ev_range = float(ev_row['Range (miles)'])

    # Read EV cost/kWh from CSV based on state
    ev_prices_df = pd.read_csv("ev_prices.csv")
    ev_price_row = ev_prices_df[ev_prices_df['State'] == state_full]
    ev_cost_per_kwh = float(ev_price_row['Cost/kWh'].values[0])

    # EV calculations: cost per mile = (Battery capacity * energy cost) / Average range
    ev_cost_per_mile = (battery_capacity * ev_cost_per_kwh) / ev_range
    total_distance_per_week = (home_work_dist * 2) * number_of_days
    ev_cost_per_week = total_distance_per_week * ev_cost_per_mile
    ev_cost_per_month = ev_cost_per_week * 4
    ev_cost_per_year = ev_cost_per_week * 52

    print("\n=== Electric Vehicle Costs ===")
    print(f"  Model: {ev_model}")
    print(f"  Cost per mile: ${ev_cost_per_mile:.4f}")
    print(f"  Cost per month: ${ev_cost_per_month:.2f}")
    print(f"  Cost per year: ${ev_cost_per_year:.2f}")

    result = {
        "inputs": {
            "home_work_distance": home_work_dist,
            "days_per_week": number_of_days,
            "state": state_full,
            "ev_model": ev_model,
            "ev_cost_per_kwh": ev_cost_per_kwh,
            "battery_capacity": battery_capacity,
            "ev_range": ev_range
        },
        "ev_costs": {
            "cost_per_mile": ev_cost_per_mile,
            "monthly": ev_cost_per_month,
            "yearly": ev_cost_per_year
        }
    }

    if include_gas and gas_mileage is not None:
        # Read gas price from CSV based on state and gas type
        gas_df = pd.read_csv("gas_prices.csv")
        gas_row = gas_df[gas_df['State'] == state_full]
        gas_price = float(gas_row[gas_type].values[0].replace('$', '').strip())

        # Gas vehicle calculations: cost per mile = Gas Price / Mileage
        gas_cost_per_mile = gas_price / gas_mileage
        gas_cost_per_week = total_distance_per_week * gas_cost_per_mile
        gas_cost_per_month = gas_cost_per_week * 4
        gas_cost_per_year = gas_cost_per_week * 52

        print("\n=== Gas Vehicle Costs ===")
        print(f"  Gas Type: {gas_type}")
        print(f"  Mileage: {gas_mileage} MPG")
        print(f"  Cost per mile: ${gas_cost_per_mile:.4f}")
        print(f"  Cost per month: ${gas_cost_per_month:.2f}")
        print(f"  Cost per year: ${gas_cost_per_year:.2f}")

        print("\n=== Savings with EV ===")
        print(f"  Monthly savings: ${gas_cost_per_month - ev_cost_per_month:.2f}")
        print(f"  Yearly savings: ${gas_cost_per_year - ev_cost_per_year:.2f}")

        result["inputs"]["gas_mileage"] = gas_mileage
        result["inputs"]["gas_type"] = gas_type
        result["inputs"]["gas_price"] = gas_price
        result["gas_costs"] = {
            "cost_per_mile": gas_cost_per_mile,
            "monthly": gas_cost_per_month,
            "yearly": gas_cost_per_year
        }
        result["savings"] = {
            "monthly": gas_cost_per_month - ev_cost_per_month,
            "yearly": gas_cost_per_year - ev_cost_per_year
        }

    return result


# Example usage
if __name__ == "__main__":
    home_address = "123 Street Address, City, State Pincode"
    work_address = "456 Street Address, City, State Pincode"

    home_coords, work_coords = get_coordinates(home_address, work_address)
    print(f"Home coordinates: {home_coords}")
    print(f"Work coordinates: {work_coords}\n")

    top_3_home, top_3_work = closest_coordinates(home_coords, work_coords)

    shortest_home_station, shortest_work_station, home_work_dist = calculate_distance(home_coords, work_coords, top_3_home, top_3_work)

    # Example with both EV and Gas analysis
    ev_models = get_ev_models()
    analysis(home_work_dist, number_of_days=5, state=shortest_home_station['State'],
             ev_model=ev_models[0], gas_mileage=27, include_gas=True)
