"""
Relief-Route Command Center Dashboard
A real-time humanitarian logistics dashboard for disaster response.
"""

import streamlit as st
import pandas as pd
import time
import os
import sys

# Add app directory to path for imports
app_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app")
sys.path.insert(0, app_dir)

from logistics import compute_loadout, plan_supply_chain, SUPPLIES
from routing import compute_route, plan_delivery_routes, get_blocked_roads, WAREHOUSES, LOCATION_COORDS

# Page configuration
st.set_page_config(
    page_title="Relief-Route Command Center",
    page_icon="🚑",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #FF4B4B;
        text-align: center;
        margin-bottom: 1rem;
    }
    .priority-critical {
        background-color: #ff4444;
        color: white;
        padding: 0.2rem 0.5rem;
        border-radius: 5px;
        font-weight: bold;
    }
    .priority-high {
        background-color: #ff8800;
        color: white;
        padding: 0.2rem 0.5rem;
        border-radius: 5px;
    }
    .priority-medium {
        background-color: #ffcc00;
        color: black;
        padding: 0.2rem 0.5rem;
        border-radius: 5px;
    }
    .priority-low {
        background-color: #44bb44;
        color: white;
        padding: 0.2rem 0.5rem;
        border-radius: 5px;
    }
    .truck-card {
        border: 2px solid #4CAF50;
        border-radius: 10px;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    .blocked-road {
        background-color: #ffebee;
        border-left: 4px solid #f44336;
        padding: 0.5rem 1rem;
        margin: 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown('<p class="main-header">🚑 Relief-Route Command Center</p>', unsafe_allow_html=True)

# Tabs for different views
tab1, tab2, tab3, tab4 = st.tabs(["📊 Situation Overview", "🗺️ Live Map", "🚚 Logistics Planning", "📍 Route Planning"])

# Sidebar
st.sidebar.title("⚙️ Controls")
auto_refresh = st.sidebar.checkbox("Auto-refresh (5s)", value=False)

# Load data function
@st.cache_data(ttl=5)
def load_data():
    """Load results from Pathway output."""
    dashboard_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(dashboard_dir)
    results_path = os.path.join(project_root, "outputs", "results.csv")
    
    if not os.path.exists(results_path):
        return None
    
    try:
        df = pd.read_csv(results_path)
        if len(df) == 0:
            return None
        return df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return None

df = load_data()

# ============ TAB 1: SITUATION OVERVIEW ============
with tab1:
    st.subheader("Humanitarian Logistics Optimizer - Real-time disaster response coordination")
    
    if df is not None and len(df) > 0:
        # Sidebar filters
        st.sidebar.subheader("Filters")
        locations = ["All"] + sorted(df['location'].dropna().unique().tolist())
        disaster_types = ["All"] + sorted(df['disaster_type'].dropna().unique().tolist())
        
        selected_location = st.sidebar.selectbox("Location", locations, key="loc_filter")
        selected_disaster = st.sidebar.selectbox("Disaster Type", disaster_types, key="dis_filter")
        min_priority = st.sidebar.slider("Minimum Priority", 0, 100, 0, key="pri_filter")
        
        # Apply filters
        filtered_df = df.copy()
        if selected_location != "All":
            filtered_df = filtered_df[filtered_df['location'] == selected_location]
        if selected_disaster != "All":
            filtered_df = filtered_df[filtered_df['disaster_type'] == selected_disaster]
        filtered_df = filtered_df[filtered_df['priority'] >= min_priority]
        filtered_df = filtered_df.sort_values('priority', ascending=False)
        
        # Metrics row
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.metric("📊 Total Reports", len(filtered_df))
        with col2:
            critical = len(filtered_df[filtered_df['priority'] >= 70])
            st.metric("🔴 Critical", critical)
        with col3:
            high = len(filtered_df[(filtered_df['priority'] >= 50) & (filtered_df['priority'] < 70)])
            st.metric("🟠 High Priority", high)
        with col4:
            infra_damage = len(filtered_df[filtered_df['infrastructure_damage'] == 'yes'])
            st.metric("🏗️ Infrastructure Damage", infra_damage)
        with col5:
            unique_locations = filtered_df['location'].nunique()
            st.metric("📍 Affected Areas", unique_locations)
        
        st.divider()
        
        # Two columns
        left_col, right_col = st.columns([2, 1])
        
        with left_col:
            st.subheader("📋 Priority Response List")
            
            def get_priority_badge(priority):
                if priority >= 70:
                    return f'<span class="priority-critical">CRITICAL ({priority})</span>'
                elif priority >= 50:
                    return f'<span class="priority-high">HIGH ({priority})</span>'
                elif priority >= 30:
                    return f'<span class="priority-medium">MEDIUM ({priority})</span>'
                else:
                    return f'<span class="priority-low">LOW ({priority})</span>'
            
            for idx, row in filtered_df.head(10).iterrows():
                badge = get_priority_badge(row['priority'])
                st.markdown(f"""
                **{row['location']}** - {row['disaster_type'].title()} {badge}
                
                📝 {str(row['text'])[:200]}{'...' if len(str(row['text'])) > 200 else ''}
                
                🏷️ `{row['category']}` | 🏗️ Infrastructure: {'⚠️ Damaged' if row['infrastructure_damage'] == 'yes' else '✅ OK'}
                """, unsafe_allow_html=True)
                st.divider()
        
        with right_col:
            st.subheader("📊 Analytics")
            
            st.markdown("**Priority Distribution**")
            priority_bins = pd.cut(filtered_df['priority'], 
                                  bins=[0, 30, 50, 70, 100], 
                                  labels=['Low', 'Medium', 'High', 'Critical'])
            st.bar_chart(priority_bins.value_counts())
            
            st.markdown("**Top Affected Locations**")
            st.bar_chart(filtered_df['location'].value_counts().head(10))
            
            st.markdown("**Disaster Types**")
            st.bar_chart(filtered_df['disaster_type'].value_counts())
    else:
        st.warning("⏳ Waiting for data... Run the Pathway processor first.")
        st.info("Run: `cd app && python main.py`")


# ============ TAB 2: LIVE MAP ============
with tab2:
    st.subheader("🗺️ Disaster Incident Map")
    
    import plotly.express as px
    
    # Function to get coordinates for a location
    def get_location_coords(location):
        """Get lat/lon for a location name."""
        location_lower = location.lower()
        for name, coords in LOCATION_COORDS.items():
            if name.lower() in location_lower or location_lower in name.lower():
                return coords
        # Default to Nepal center
        return (27.7172, 85.3240)
    
    if df is not None and len(df) > 0:
        # Map legend
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.markdown("🔴 **Critical** (70+)")
        with col2:
            st.markdown("🟠 **High** (50-69)")
        with col3:
            st.markdown("🟡 **Medium** (30-49)")
        with col4:
            st.markdown("🟢 **Low** (<30)")
        with col5:
            st.markdown("🔵 **Warehouse**")
        
        # Prepare map data for incidents
        map_points = []
        
        import random
        random.seed(42)  # Consistent positions
        
        for idx, row in df.iterrows():
            coords = get_location_coords(row['location'])
            priority = row['priority']
            
            # Color based on priority
            if priority >= 70:
                color = "Critical"
            elif priority >= 50:
                color = "High"
            elif priority >= 30:
                color = "Medium"
            else:
                color = "Low"
            
            # Add small random offset to prevent overlapping markers
            lat_offset = random.uniform(-0.08, 0.08)
            lon_offset = random.uniform(-0.08, 0.08)
            
            map_points.append({
                'lat': coords[0] + lat_offset,
                'lon': coords[1] + lon_offset,
                'Location': row['location'],
                'Priority': int(priority),
                'Type': row['disaster_type'],
                'Severity': color,
                'size': max(15, int(priority) / 5),
                'Category': 'Incident'
            })
        
        # Add warehouse locations
        for region, warehouse in WAREHOUSES.items():
            map_points.append({
                'lat': warehouse['coordinates'][0],
                'lon': warehouse['coordinates'][1],
                'Location': warehouse['name'],
                'Priority': 0,
                'Type': 'Warehouse',
                'Severity': 'Warehouse',
                'size': 20,
                'Category': 'Warehouse'
            })
        
        map_df = pd.DataFrame(map_points)
        
        # Show count
        incident_count = len(df)
        warehouse_count = len(WAREHOUSES)
        st.caption(f"📍 {incident_count} incidents | 🏭 {warehouse_count} warehouses — **Hover over markers for details**")
        
        st.divider()
        
        # Color mapping
        color_map = {
            "Critical": "#FF0000",
            "High": "#FF8C00", 
            "Medium": "#FFD700",
            "Low": "#32CD32",
            "Warehouse": "#1E90FF"
        }
        
        # Create Plotly scatter map with hover
        fig = px.scatter_mapbox(
            map_df,
            lat="lat",
            lon="lon",
            color="Severity",
            size="size",
            hover_name="Location",
            hover_data={
                "Priority": True,
                "Type": True,
                "Severity": True,
                "lat": ":.4f",
                "lon": ":.4f",
                "size": False,
                "Category": False
            },
            color_discrete_map=color_map,
            category_orders={"Severity": ["Critical", "High", "Medium", "Low", "Warehouse"]},
            zoom=6,
            height=500,
            mapbox_style="carto-positron"
        )
        
        fig.update_layout(
            margin={"r": 0, "t": 0, "l": 0, "b": 0},
            legend=dict(
                yanchor="top",
                y=0.99,
                xanchor="left",
                x=0.01,
                bgcolor="rgba(255,255,255,0.8)"
            )
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Stats below map
        st.divider()
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 📍 Incident Locations")
            location_summary = df.groupby('location').agg({
                'priority': ['count', 'max', 'mean']
            }).round(1)
            location_summary.columns = ['Incidents', 'Max Priority', 'Avg Priority']
            location_summary = location_summary.sort_values('Max Priority', ascending=False)
            st.dataframe(location_summary, use_container_width=True)
        
        with col2:
            st.markdown("### 🏭 Warehouse Coverage")
            for region, warehouse in WAREHOUSES.items():
                st.markdown(f"""
                **{warehouse['name']}**
                - 📍 {warehouse['location']}
                - 🚚 Capacity: {warehouse['capacity_trucks']} trucks
                - 📦 Supplies: {'✅ Available' if warehouse['supplies_available'] else '❌ Low'}
                """)
        
    else:
        st.warning("⏳ Waiting for incident data...")
        
        import plotly.express as px
        
        # Show empty map centered on Nepal with just warehouses
        warehouse_data = []
        for region, warehouse in WAREHOUSES.items():
            warehouse_data.append({
                'lat': warehouse['coordinates'][0],
                'lon': warehouse['coordinates'][1],
                'Location': warehouse['name'],
            })
        
        wh_df = pd.DataFrame(warehouse_data)
        fig = px.scatter_mapbox(
            wh_df, lat="lat", lon="lon", hover_name="Location",
            zoom=5, height=400, mapbox_style="carto-positron"
        )
        fig.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0})
        st.plotly_chart(fig, use_container_width=True)
        st.info("Run the processor to see incident markers on the map.")


# ============ TAB 3: LOGISTICS PLANNING ============
with tab3:
    st.subheader("🚚 Supply Chain & Truck Load-out Planning")
    
    if df is not None and len(df) > 0:
        # Configuration
        col1, col2 = st.columns(2)
        with col1:
            available_trucks = st.number_input("Available Trucks", min_value=1, max_value=50, value=5)
        with col2:
            truck_size = st.selectbox("Default Truck Size", ["small", "medium", "large"], index=1)
        
        st.divider()
        
        # Prepare incidents for planning
        incidents = filtered_df.to_dict('records') if 'filtered_df' in dir() else df.head(20).to_dict('records')
        
        # Generate supply chain plan
        if st.button("🔄 Generate Deployment Plan", type="primary"):
            with st.spinner("Computing optimal deployments..."):
                plan = plan_supply_chain(incidents, available_trucks=available_trucks)
                st.session_state['deployment_plan'] = plan
        
        # Display plan
        if 'deployment_plan' in st.session_state:
            plan = st.session_state['deployment_plan']
            
            # Summary metrics
            st.subheader("📦 Deployment Summary")
            m1, m2, m3, m4 = st.columns(4)
            with m1:
                st.metric("🚚 Trucks Deployed", plan['trucks_used'])
            with m2:
                st.metric("📦 Total Supplies", f"{plan['total_supplies_kg']:,} kg")
            with m3:
                st.metric("👥 Est. People Helped", f"{plan['estimated_people_helped']:,}")
            with m4:
                st.metric("⚠️ Unserved Areas", plan['unserved_incidents'])
            
            st.divider()
            
            # Truck deployments
            st.subheader("🚚 Truck Deployments")
            
            for deployment in plan['deployments']:
                with st.expander(f"**{deployment['truck_id']}** → {deployment['destination']} (Priority: {deployment['priority_score']})", expanded=False):
                    
                    col1, col2 = st.columns([1, 2])
                    
                    with col1:
                        st.markdown(f"""
                        **Truck Details**
                        - 🚚 Size: {deployment['truck_size'].upper()}
                        - 📍 Destination: {deployment['destination']}
                        - 🌊 Disaster: {deployment['disaster_type'].title()}
                        - ⚖️ Load: {deployment['loadout']['total_weight_kg']} kg
                        - 📊 Capacity Used: {deployment['loadout']['capacity_used_pct']}%
                        """)
                    
                    with col2:
                        st.markdown("**Load-out Manifest**")
                        loadout_df = pd.DataFrame(deployment['loadout']['supplies'])
                        if not loadout_df.empty:
                            st.dataframe(
                                loadout_df[['name', 'quantity', 'weight_kg', 'category']],
                                hide_index=True,
                                use_container_width=True
                            )
                    
                    st.markdown(f"**🎯 Priority Supplies:** {', '.join(deployment['loadout']['priority_supplies'])}")
        
        st.divider()
        
        # Manual load-out calculator
        st.subheader("🧮 Manual Load-out Calculator")
        
        with st.form("loadout_form"):
            col1, col2, col3 = st.columns(3)
            with col1:
                calc_disaster = st.selectbox("Disaster Type", ["earthquake", "flood", "landslide", "unknown"])
                calc_priority = st.slider("Priority Score", 0, 100, 70)
            with col2:
                calc_category = st.selectbox("Category", [
                    "injured_or_dead_people",
                    "missing_trapped_or_found_people", 
                    "infrastructure_and_utilities_damage",
                    "displaced_people_and_evacuations",
                    "other_useful_information"
                ])
                calc_infra = st.selectbox("Infrastructure Damage", ["yes", "no"])
            with col3:
                calc_truck = st.selectbox("Truck Size", ["small", "medium", "large"], index=1)
                calc_population = st.number_input("Est. Population", min_value=10, max_value=10000, value=100)
            
            if st.form_submit_button("Calculate Optimal Load-out"):
                loadout = compute_loadout(
                    disaster_type=calc_disaster,
                    priority_score=calc_priority,
                    category=calc_category,
                    infrastructure_damage=calc_infra,
                    truck_size=calc_truck,
                    population_estimate=calc_population
                )
                
                st.success(f"✅ Optimal load-out computed for {calc_truck} truck")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Total Weight", f"{loadout['total_weight_kg']} kg")
                    st.metric("Capacity Used", f"{loadout['capacity_used_pct']}%")
                with col2:
                    st.metric("Est. People Helped", loadout['estimated_people_helped'])
                    st.markdown(f"**Priority Items:** {', '.join(loadout['priority_supplies'])}")
                
                st.dataframe(pd.DataFrame(loadout['supplies']), hide_index=True)
    else:
        st.warning("⏳ Load incident data first from Situation Overview tab")


# ============ TAB 4: ROUTE PLANNING ============
with tab4:
    st.subheader("📍 Route Planning & Road Conditions")
    
    # Road blockages
    st.markdown("### 🚧 Current Road Blockages")
    
    blocked_roads = get_blocked_roads()
    if blocked_roads:
        for road in blocked_roads:
            st.markdown(f"""
            <div class="blocked-road">
                <strong>🚫 {road['from']} ↔ {road['to']}</strong><br>
                Reason: {road['reason']} | Severity: {road['severity'].upper()}
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("No road blockages reported")
    
    st.divider()
    
    # Warehouse info
    st.markdown("### 🏭 Available Warehouses")
    warehouse_df = pd.DataFrame([
        {"Region": k, "Name": v["name"], "Location": v["location"], "Trucks": v["capacity_trucks"]}
        for k, v in WAREHOUSES.items()
    ])
    st.dataframe(warehouse_df, hide_index=True, use_container_width=True)
    
    st.divider()
    
    # Route calculator
    st.markdown("### 📍 Route Calculator")
    
    with st.form("route_form"):
        col1, col2 = st.columns(2)
        with col1:
            origin = st.text_input("Origin", value="Kathmandu Central Warehouse")
        with col2:
            destination = st.text_input("Destination", value="Gorkha")
        
        avoid_blocked = st.checkbox("Avoid blocked roads", value=True)
        
        if st.form_submit_button("Calculate Route"):
            route = compute_route(origin, destination, avoid_blocked)
            
            # Display route info
            if route.route_type == "blocked" and not avoid_blocked:
                st.error("🚫 Route is completely blocked!")
            else:
                status_color = "🟢" if route.road_conditions == "clear" else "🟡" if route.road_conditions == "partial_blockage" else "🔴"
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("📏 Distance", f"{route.distance_km} km")
                with col2:
                    st.metric("⏱️ Est. Time", f"{route.estimated_time_hours} hours")
                with col3:
                    st.metric("Road Conditions", f"{status_color} {route.road_conditions.replace('_', ' ').title()}")
                
                st.markdown(f"**Route Type:** {route.route_type.upper()}")
                st.markdown(f"**Waypoints:** {' → '.join(route.waypoints)}")
                
                if route.warnings:
                    st.warning("**Warnings:**")
                    for warning in route.warnings:
                        st.markdown(f"- {warning}")
    
    st.divider()
    
    # Multi-destination route planning
    if df is not None and len(df) > 0:
        st.markdown("### 🚚 Multi-Destination Route Plan")
        
        if st.button("🔄 Plan All Delivery Routes"):
            with st.spinner("Computing routes for all priority destinations..."):
                # Get top priority destinations
                destinations = df.nlargest(10, 'priority').to_dict('records')
                routes = plan_delivery_routes(destinations)
                
                # Display routes
                route_df = pd.DataFrame(routes)
                route_df['warnings_count'] = route_df['warnings'].apply(len)
                
                st.dataframe(
                    route_df[['destination', 'priority', 'warehouse', 'distance_km', 
                             'estimated_time_hours', 'route_type', 'road_conditions', 'warnings_count']],
                    hide_index=True,
                    use_container_width=True
                )
                
                # Summary
                total_distance = route_df['distance_km'].sum()
                avg_time = route_df['estimated_time_hours'].mean()
                blocked_count = len(route_df[route_df['route_type'] == 'alternative'])
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Distance", f"{total_distance:.0f} km")
                with col2:
                    st.metric("Avg Delivery Time", f"{avg_time:.1f} hours")
                with col3:
                    st.metric("Routes with Detours", blocked_count)


# ============ SIDEBAR EXPORT ============
st.sidebar.divider()
st.sidebar.subheader("📥 Export")

if df is not None:
    csv = df.to_csv(index=False)
    st.sidebar.download_button(
        label="Download CSV",
        data=csv,
        file_name="relief_route_export.csv",
        mime="text/csv"
    )

# Footer
st.sidebar.divider()
st.sidebar.markdown("**Relief-Route** v2.0")
st.sidebar.markdown("Powered by Pathway + Gemini")

# Auto-refresh
if auto_refresh:
    time.sleep(5)
    st.rerun()
