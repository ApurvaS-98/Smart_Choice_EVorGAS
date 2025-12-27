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
    geolocator = Nominatim(user_agent="ev_gas_analysis")

    home_location = geolocator.geocode(home_address)
    work_location = geolocator.geocode(work_address)

    home_coords = (home_location.latitude, home_location.longitude)
    work_coords = (work_location.latitude, work_location.longitude)

    return home_coords, work_coords


def closest_coordinates(home_coords):
    """Find the 3 closest fuel stations to home coordinates."""
    df = pd.read_csv("fuel_stations_cleaned.csv")

    distances = []
    for idx, row in df.iterrows():
        station_coords = (row['Latitude'], row['Longitude'])
        dist = geodesic(home_coords, station_coords).miles
        distances.append(dist)

    df['distance'] = distances
    df_sorted = df.sort_values('distance')
    top_3 = df_sorted.head(3)

    result = top_3[['Street Address', 'City', 'State', 'ZIP', 'Latitude', 'Longitude', 'distance']]
    print("Top 3 closest fuel stations:")
    print(result.to_string(index=False))

    return result


def calculate_distance(home_coords, work_coords, top_3_stations):
    """Calculate road distances using OpenRouteService API."""
    base_url = "https://api.openrouteservice.org/v2/directions/driving-car"
    headers = {"Authorization": ORS_API_KEY}

    shortest_distance = float('inf')
    shortest_station = None

    for idx, row in top_3_stations.iterrows():
        station_coords = (row['Longitude'], row['Latitude'])  # ORS uses lon, lat
        home_lonlat = (home_coords[1], home_coords[0])

        params = {
            "start": f"{home_lonlat[0]},{home_lonlat[1]}",
            "end": f"{station_coords[0]},{station_coords[1]}"
        }

        response = requests.get(base_url, headers=headers, params=params)
        data = response.json()

        distance_meters = data['features'][0]['properties']['segments'][0]['distance']
        distance_miles = distance_meters * 0.000621371

        if distance_miles < shortest_distance:
            shortest_distance = distance_miles
            shortest_station = {
                'Street Address': row['Street Address'],
                'City': row['City'],
                'State': row['State'],
                'ZIP': row['ZIP'],
                'distance_miles': distance_miles
            }

    # Calculate home to work distance
    home_lonlat = (home_coords[1], home_coords[0])
    work_lonlat = (work_coords[1], work_coords[0])

    params = {
        "start": f"{home_lonlat[0]},{home_lonlat[1]}",
        "end": f"{work_lonlat[0]},{work_lonlat[1]}"
    }

    response = requests.get(base_url, headers=headers, params=params)
    data = response.json()

    home_work_dist = data['features'][0]['properties']['segments'][0]['distance'] * 0.000621371

    print(f"\nClosest station by road:")
    print(f"  Address: {shortest_station['Street Address']}")
    print(f"  City: {shortest_station['City']}, {shortest_station['State']} {shortest_station['ZIP']}")
    print(f"  Road distance: {shortest_station['distance_miles']:.2f} miles")
    print(f"\nHome to Work distance: {home_work_dist:.2f} miles")

    return shortest_station, home_work_dist


def analysis(home_work_dist, number_of_days):
    """Analyze cost difference between gas and electric vehicles."""
    # Constants
    gas_price = 2.84  # $ per gallon
    gas_mileage = 20  # miles per gallon
    ev_charge_cost = 20  # $ per full charge
    ev_range = 275  # miles per charge

    # Gas vehicle calculations
    gas_cost_per_day = (home_work_dist * 2) / gas_mileage * gas_price
    gas_cost_per_week = gas_cost_per_day * number_of_days
    gas_cost_per_month = gas_cost_per_week * 4
    gas_cost_per_year = gas_cost_per_week * 52

    # EV calculations
    ev_cost_per_mile = ev_charge_cost / ev_range
    ev_cost_per_day = (home_work_dist * 2) * ev_cost_per_mile
    ev_cost_per_week = ev_cost_per_day * number_of_days
    ev_cost_per_month = ev_cost_per_week * 4
    ev_cost_per_year = ev_cost_per_week * 52

    print("\n=== Gas Vehicle Costs ===")
    print(f"  Cost per day: ${gas_cost_per_day:.2f}")
    print(f"  Cost per week: ${gas_cost_per_week:.2f}")
    print(f"  Cost per month: ${gas_cost_per_month:.2f}")
    print(f"  Cost per year: ${gas_cost_per_year:.2f}")

    print("\n=== Electric Vehicle Costs ===")
    print(f"  Cost per day: ${ev_cost_per_day:.2f}")
    print(f"  Cost per week: ${ev_cost_per_week:.2f}")
    print(f"  Cost per month: ${ev_cost_per_month:.2f}")
    print(f"  Cost per year: ${ev_cost_per_year:.2f}")

    print("\n=== Savings with EV ===")
    print(f"  Weekly savings: ${gas_cost_per_week - ev_cost_per_week:.2f}")
    print(f"  Monthly savings: ${gas_cost_per_month - ev_cost_per_month:.2f}")
    print(f"  Yearly savings: ${gas_cost_per_year - ev_cost_per_year:.2f}")


# Example usage
if __name__ == "__main__":
    home_address = "1600 Amphitheatre Parkway, Mountain View, CA 94043"
    work_address = "1 Hacker Way, Menlo Park, CA 94025"

    home_coords, work_coords = get_coordinates(home_address, work_address)
    print(f"Home coordinates: {home_coords}")
    print(f"Work coordinates: {work_coords}\n")

    top_3 = closest_coordinates(home_coords)

    shortest_station, home_work_dist = calculate_distance(home_coords, work_coords, top_3)

    analysis(home_work_dist, number_of_days=5)
