import streamlit as st
import pandas as pd
import altair as alt
from ev_gas_analysis import get_coordinates, closest_coordinates, calculate_distance, analysis, get_ev_models

# Custom CSS for placeholder styling (matches text input placeholder style)
st.markdown("""
<style>
    /* Style for selectbox placeholder text - similar to text input placeholders */
    div[data-baseweb="select"] > div:first-child {
        color: rgba(250, 250, 250, 0.6) !important;
    }
</style>
""", unsafe_allow_html=True)

st.title("EV vs Gas Cost Analysis")

# Input Section
st.subheader("Enter Your Details")

home_address = st.text_input("Home Address", placeholder="e.g., 6805 Wood Hollow Dr, Austin, TX 78731")
work_address = st.text_input("Work Address", placeholder="e.g., 2601 N Lamar Blvd, Austin, TX 78705")

# Days selection with placeholder
days_options = ["Select days per week"] + [str(i) for i in range(1, 8)]
selected_days = st.selectbox("Days Commuting Per Week", days_options, index=0)

# Radio buttons for analysis type
analysis_type = st.radio(
    "Select analysis type:",
    ["EV Only", "Both EV and Gas Vehicle"],
    horizontal=True
)

# EV Model dropdown with placeholder
ev_models = get_ev_models()
ev_options = ["Select an EV Model"] + ev_models
selected_ev_model = st.selectbox("Select EV Model", ev_options, index=0)

# Gas mileage and gas type inputs (only shown if both is selected)
gas_mileage = None
gas_type = None
if analysis_type == "Both EV and Gas Vehicle":
    gas_mileage = st.number_input(
        "Gas Vehicle Mileage (MPG)",
        min_value=10.0,
        max_value=60.0,
        value=27.0,
        step=1.0,
        help="Average mileage for gas vehicle is 27 MPG"
    )
    gas_type = st.selectbox(
        "Select Gas Type",
        ["Regular", "Mid-grade", "Premium"]
    )

# Analysis Button
if st.button("Analyze Costs"):
    # Validate inputs
    if selected_days == "Select days per week":
        st.error("Please select the number of days commuting per week.")
        st.stop()

    if selected_ev_model == "Select an EV Model":
        st.error("Please select an EV model.")
        st.stop()

    number_of_days = int(selected_days)

    # Get coordinates
    home_coords, work_coords = get_coordinates(home_address, work_address)

    # Find closest EV stations for both home and work
    top_3_home, top_3_work = closest_coordinates(home_coords, work_coords)

    # Calculate distances
    shortest_home_station, shortest_work_station, home_work_dist = calculate_distance(home_coords, work_coords, top_3_home, top_3_work)

    # Run analysis
    include_gas = analysis_type == "Both EV and Gas Vehicle"
    results = analysis(
        home_work_dist,
        number_of_days,
        shortest_home_station['State'],
        selected_ev_model,
        gas_mileage=gas_mileage,
        gas_type=gas_type,
        include_gas=include_gas
    )

    # Display Results Section
    st.subheader("Analysis Results")

    # Distance and pricing info
    st.write(f"**Home to Work Distance:** {results['inputs']['home_work_distance']:.2f} miles")
    st.write(f"**State:** {results['inputs']['state']}")
    st.write(f"**EV Model:** {results['inputs']['ev_model']}")
    st.write(f"**EV Rate:** ${results['inputs']['ev_cost_per_kwh']:.3f}/kWh")

    # Closest stations info
    st.write(f"**Closest Station to Home:** {shortest_home_station['Street Address']}, {shortest_home_station['City']}, {shortest_home_station['State']} ({shortest_home_station['distance_miles']:.2f} miles)")
    st.write(f"**Closest Station to Work:** {shortest_work_station['Street Address']}, {shortest_work_station['City']}, {shortest_work_station['State']} ({shortest_work_station['distance_miles']:.2f} miles)")

    if include_gas:
        st.write(f"**Gas Type:** {results['inputs']['gas_type']}")
        st.write(f"**Gas Price:** ${results['inputs']['gas_price']:.2f}/gallon")
        st.write(f"**Gas Mileage:** {results['inputs']['gas_mileage']} MPG")

        # Savings highlight
        yearly_savings = results['savings']['yearly']
        if yearly_savings > 0:
            st.success(f"You save ${yearly_savings:.2f} per year with an EV!")
        else:
            st.warning(f"Gas vehicle saves ${-yearly_savings:.2f} per year compared to EV.")

        # Dashboard Section - Cost per mile bar chart
        st.subheader("Dashboard - Cost Per Mile Comparison")

        cost_per_mile_data = pd.DataFrame({
            'Vehicle Type': ['Gas Vehicle', 'Electric Vehicle'],
            'Cost per Mile ($)': [results['gas_costs']['cost_per_mile'], results['ev_costs']['cost_per_mile']]
        })

        bar_chart = alt.Chart(cost_per_mile_data).mark_bar().encode(
            x=alt.X('Vehicle Type:N', title='Vehicle Type'),
            y=alt.Y('Cost per Mile ($):Q', title='Cost per Mile ($)'),
            color=alt.Color('Vehicle Type:N', scale=alt.Scale(domain=['Gas Vehicle', 'Electric Vehicle'], range=['#FF6B6B', '#4ECDC4']))
        ).properties(
            width=500,
            height=300
        )

        st.altair_chart(bar_chart, use_container_width=True)

        # Grouped Bar Chart for Cost Comparison
        st.subheader("Cost Savings Visualization")

        # Create data for grouped bar chart
        comparison_data = pd.DataFrame({
            'Period': ['Monthly', 'Monthly', 'Yearly', 'Yearly'],
            'Vehicle Type': ['Gas Vehicle', 'Electric Vehicle', 'Gas Vehicle', 'Electric Vehicle'],
            'Cost ($)': [
                results['gas_costs']['monthly'],
                results['ev_costs']['monthly'],
                results['gas_costs']['yearly'],
                results['ev_costs']['yearly']
            ]
        })

        grouped_bar = alt.Chart(comparison_data).mark_bar().encode(
            x=alt.X('Period:N', title='Period', axis=alt.Axis(labelAngle=0)),
            y=alt.Y('Cost ($):Q', title='Cost ($)'),
            color=alt.Color('Vehicle Type:N', scale=alt.Scale(domain=['Gas Vehicle', 'Electric Vehicle'], range=['#FF6B6B', '#4ECDC4'])),
            xOffset='Vehicle Type:N'
        ).properties(
            width=500,
            height=350
        )

        st.altair_chart(grouped_bar, use_container_width=True)

        # Savings summary
        st.subheader("Savings Summary")
        savings_data = pd.DataFrame({
            'Period': ['Monthly', 'Yearly'],
            'Savings ($)': [f"${results['savings']['monthly']:.2f}", f"${results['savings']['yearly']:.2f}"]
        })
        st.table(savings_data)

    else:
        # EV Only display
        st.subheader("Electric Vehicle Costs")
        st.metric("Cost per Mile", f"${results['ev_costs']['cost_per_mile']:.4f}")
        st.metric("Monthly Cost", f"${results['ev_costs']['monthly']:.2f}")
        st.metric("Yearly Cost", f"${results['ev_costs']['yearly']:.2f}")

        # EV specs info
        st.write(f"**Battery Capacity:** {results['inputs']['battery_capacity']} kWh")
        st.write(f"**Range:** {results['inputs']['ev_range']} miles")
