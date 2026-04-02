# bus_utils.py
import streamlit as st
from datetime import datetime, timedelta

def create_bus(bus_id, name, source, destination, route, dep, arr, price, stops, operating_days):
    """Create a bus with seat layout"""
    seats = []
    # Seats 1-10: male only, 11-15: female only, 16-20: any gender
    for i in range(1, 21):
        if i <= 10:
            gender = "male"
        elif i <= 15:
            gender = "female"
        else:
            gender = "any"
        # Pre‑book a few seats for demo
        booked = i in [3, 5, 12, 18]
        seats.append({"num": i, "gender": gender, "booked": booked})
    return {
        "id": bus_id, "name": name, "source": source, "destination": destination,
        "route": route, "dep": dep, "arr": arr, "price": price,
        "stops": stops, "seats": seats, "operating_days": operating_days
    }

def init_session_state():
    """Initialize all session state variables"""
    if "users" not in st.session_state:
        st.session_state.users = {}  # {username: {"password": pwd, "gender": gender}}
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if "username" not in st.session_state:
        st.session_state.username = ""
    if "buses" not in st.session_state:
        # Define available cities
        st.session_state.cities = ["Mumbai", "Delhi", "Bangalore", "Chennai", "Kolkata", "Hyderabad", "Pune", "Ahmedabad", "Jaipur"]
        
        # Create buses with operating days
        st.session_state.buses = [
            create_bus(1, "City Express", "Mumbai", "Pune", "Mumbai → Pune", "08:00", "12:00", 25.0,
                      "Downtown, Central", [0,1,2,3,4,5,6]),  # All days
            create_bus(2, "Night Rider", "Delhi", "Jaipur", "Delhi → Jaipur", "22:30", "05:30", 35.0,
                      "Northgate, Eastside", [0,1,2,3,4,5,6]),  # All days
            create_bus(3, "Royal Travels", "Bangalore", "Chennai", "Bangalore → Chennai", "09:00", "15:00", 40.0,
                      "Electronic City, Vellore", [0,2,4,6]),  # Mon, Wed, Fri, Sun
            create_bus(4, "Morning Star", "Mumbai", "Ahmedabad", "Mumbai → Ahmedabad", "06:00", "14:00", 45.0,
                      "Borivali, Surat", [1,3,5]),  # Tue, Thu, Sat
            create_bus(5, "Coastal Express", "Chennai", "Bangalore", "Chennai → Bangalore", "20:00", "06:00", 38.0,
                      "Tambaram, Vellore", [0,1,2,3,4,5,6]),  # All days
            create_bus(6, "Deccan Queen", "Hyderabad", "Bangalore", "Hyderabad → Bangalore", "07:30", "15:30", 50.0,
                      "Kurnool, Anantapur", [0,2,4]),  # Mon, Wed, Fri
            create_bus(7, "Gujarat Express", "Ahmedabad", "Mumbai", "Ahmedabad → Mumbai", "21:00", "06:00", 48.0,
                      "Vadodara, Surat", [1,3,5,6]),  # Tue, Thu, Sat, Sun
            create_bus(8, "East Coast Express", "Kolkata", "Chennai", "Kolkata → Chennai", "10:00", "22:00", 65.0,
                      "Bhubaneswar, Vizag", [0,3,6]),  # Mon, Thu, Sun
        ]
        
        # Store bookings
        st.session_state.bookings = {}  # {username: [{"bus": bus, "seat": seat, "date": date}]}
    
    if "user_gender" not in st.session_state:
        st.session_state.user_gender = "male"
    if "search_criteria" not in st.session_state:
        st.session_state.search_criteria = {
            "source": "",
            "destination": "",
            "date": "",
            "searched": False
        }
    if "show_bookings" not in st.session_state:
        st.session_state.show_bookings = False

def show_login():
    """Display login form"""
    st.markdown("### 🔐 Login to Your Account")
    with st.form("login_form"):
        username = st.text_input("Username", placeholder="Enter your username")
        password = st.text_input("Password", type="password", placeholder="Enter your password")
        submitted = st.form_submit_button("Login", use_container_width=True)
        
        if submitted:
            if username in st.session_state.users:
                if st.session_state.users[username]["password"] == password:
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.session_state.user_gender = st.session_state.users[username]["gender"]
                    st.rerun()
                else:
                    st.error("❌ Incorrect password!")
            else:
                st.error("❌ User not found! Please sign up first.")

def show_signup():
    """Display signup form"""
    st.markdown("### 📝 Create New Account")
    with st.form("signup_form"):
        new_username = st.text_input("Username", placeholder="Choose a username")
        new_password = st.text_input("Password", type="password", placeholder="Choose a password")
        confirm_password = st.text_input("Confirm Password", type="password", placeholder="Confirm your password")
        gender = st.radio("Gender", ["male", "female"], horizontal=True)
        submitted = st.form_submit_button("Sign Up", use_container_width=True)
        
        if submitted:
            if not new_username or not new_password:
                st.error("❌ Please fill all fields!")
            elif new_password != confirm_password:
                st.error("❌ Passwords do not match!")
            elif new_username in st.session_state.users:
                st.warning("⚠️ Username already exists! Please choose another one.")
            else:
                st.session_state.users[new_username] = {
                    "password": new_password,
                    "gender": gender
                }
                st.success("✅ Account created successfully! Please login.")
                st.balloons()

def search_buses(source, destination, travel_date):
    """Filter buses based on search criteria"""
    filtered_buses = []
    # Get day of week (0=Monday, 6=Sunday)
    day_of_week = travel_date.weekday()
    
    for bus in st.session_state.buses:
        if bus['source'] == source and bus['destination'] == destination:
            # Check if bus operates on this day
            if day_of_week in bus['operating_days']:
                # Create a copy of the bus with the travel date
                bus_copy = bus.copy()
                bus_copy['date'] = travel_date.strftime("%Y-%m-%d")
                filtered_buses.append(bus_copy)
    return filtered_buses

def get_unique_routes():
    """Get unique source-destination pairs"""
    routes = set()
    for bus in st.session_state.buses:
        routes.add((bus['source'], bus['destination']))
    return sorted(list(routes))

def display_my_bookings():
    """Display user's bookings"""
    st.title("🎫 My Bookings")
    username = st.session_state.username
    
    if username in st.session_state.bookings and st.session_state.bookings[username]:
        bookings = st.session_state.bookings[username]
        st.success(f"📋 You have {len(bookings)} booking(s)")
        
        for idx, booking in enumerate(bookings, 1):
            with st.expander(f"Booking #{idx} - {booking['bus']['name']}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**🚌 Bus:** {booking['bus']['name']}")
                    st.write(f"**📍 Route:** {booking['bus']['source']} → {booking['bus']['destination']}")
                    st.write(f"**📅 Date:** {booking['date']}")
                with col2:
                    st.write(f"**💺 Seat Number:** {booking['seat']}")
                    st.write(f"**⏰ Departure:** {booking['bus']['dep']}")
                    st.write(f"**💰 Price:** ₹{booking['bus']['price']}")
                
                if st.button(f"❌ Cancel Booking", key=f"cancel_{idx}"):
                    # Remove booking
                    st.session_state.bookings[username].pop(idx-1)
                    st.success("Booking cancelled successfully!")
                    st.rerun()
    else:
        st.info("📭 You haven't booked any tickets yet. Search and book your first journey!")
        if st.button("🔍 Search Buses"):
            st.session_state.show_bookings = False
            st.rerun()
