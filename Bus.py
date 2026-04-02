# bus_reservation_system.py
import streamlit as st
from utils import init_session_state, show_login, show_signup, search_buses, get_unique_routes, display_my_bookings

# ---------- INITIALIZE SESSION STATE ----------
init_session_state()

# ---------- LOGIN / SIGNUP ----------
def login_signup():
    st.title("🚌 Bus Reservation System")
    st.markdown("---")
    
    tab1, tab2 = st.tabs(["🔐 Login", "📝 Sign Up"])
    
    with tab1:
        show_login()
    
    with tab2:
        show_signup()

# ---------- MAIN APP (LOGGED IN) ----------
if not st.session_state.logged_in:
    login_signup()
    st.stop()

# Show My Bookings if requested
if st.session_state.show_bookings:
    display_my_bookings()
    if st.button("← Back to Search"):
        st.session_state.show_bookings = False
        st.rerun()
    st.stop()

# Main app content
st.sidebar.title(f"👋 Welcome, {st.session_state.username}")
st.sidebar.markdown("---")

# Gender selection in sidebar
st.sidebar.subheader("👤 Your Information")
st.sidebar.write(f"**Gender:** {st.session_state.user_gender.capitalize()}")
if st.sidebar.button("🔄 Change Gender", use_container_width=True):
    new_gender = "female" if st.session_state.user_gender == "male" else "male"
    st.session_state.user_gender = new_gender
    if st.session_state.username in st.session_state.users:
        st.session_state.users[st.session_state.username]["gender"] = new_gender
    st.rerun()

st.sidebar.markdown("---")

# My Bookings section in sidebar
st.sidebar.subheader("📋 My Bookings")
booking_count = len(st.session_state.bookings.get(st.session_state.username, []))
st.sidebar.write(f"**Total Bookings:** {booking_count}")
if st.sidebar.button("🎫 View My Bookings", use_container_width=True):
    st.session_state.show_bookings = True
    st.rerun()

st.sidebar.markdown("---")

if st.sidebar.button("🚪 Logout", use_container_width=True):
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.rerun()

# Main content area
st.title("🚍 Bus Reservation System")
st.markdown("### Find and Book Your Journey")

# Search Section
st.markdown("---")
st.subheader("🔍 Search Buses")

col1, col2, col3 = st.columns(3)

with col1:
    source = st.selectbox(
        "From 🏁",
        ["Select source city"] + st.session_state.cities,
        index=0
    )

with col2:
    # Get available destinations based on source
    if source != "Select source city":
        available_destinations = ["Select destination city"]
        for bus in st.session_state.buses:
            if bus['source'] == source and bus['destination'] not in available_destinations:
                available_destinations.append(bus['destination'])
    else:
        available_destinations = ["Select source city first"]
    
    destination = st.selectbox(
        "To 🏁",
        available_destinations,
        index=0
    )

with col3:
    # Date selection (next 30 days only)
    from datetime import datetime, timedelta
    min_date = datetime.now().date()
    max_date = min_date + timedelta(days=30)
    travel_date = st.date_input(
        "Travel Date 📅",
        min_value=min_date,
        max_value=max_date,
        value=min_date + timedelta(days=1)
    )

# Search button
col1, col2, col3 = st.columns([1,2,1])
with col2:
    search_clicked = st.button("🔍 Search Buses", use_container_width=True, type="primary")

if search_clicked:
    if source == "Select source city" or destination == "Select destination city" or source == destination:
        st.error("❌ Please select valid source and destination cities!")
    else:
        st.session_state.search_criteria = {
            "source": source,
            "destination": destination,
            "date": travel_date,
            "searched": True
        }
        st.rerun()

# Display search results
if st.session_state.search_criteria["searched"]:
    st.markdown("---")
    st.subheader(f"🚌 Buses from {st.session_state.search_criteria['source']} to {st.session_state.search_criteria['destination']}")
    st.caption(f"📅 Travel Date: {st.session_state.search_criteria['date'].strftime('%A, %B %d, %Y')}")
    
    # Search for buses
    filtered_buses = search_buses(
        st.session_state.search_criteria["source"],
        st.session_state.search_criteria["destination"],
        st.session_state.search_criteria["date"]
    )
    
    if filtered_buses:
        st.success(f"✅ Found {len(filtered_buses)} bus(es) operating on this day")
        
        for bus in filtered_buses:
            # Calculate duration
            dep_hour = int(bus['dep'].split(':')[0])
            dep_min = int(bus['dep'].split(':')[1])
            arr_hour = int(bus['arr'].split(':')[0])
            arr_min = int(bus['arr'].split(':')[1])
            
            duration_hours = arr_hour - dep_hour
            if duration_hours < 0:
                duration_hours += 24
            
            with st.expander(f"🚌 **{bus['name']}**  |  ⏰ {bus['dep']} - {bus['arr']}  |  💰 ₹{bus['price']}", expanded=True):
                # Basic info
                col1, col2, col3 = st.columns(3)
                col1.metric("🕐 Departure", bus['dep'])
                col2.metric("🕒 Arrival", bus['arr'])
                col3.metric("⏱️ Duration", f"{duration_hours}h")
                
                st.write(f"**📍 Route:** {bus['route']}")
                st.write(f"**🛑 Stops:** {bus['stops']}")
                
                # Seat availability
                seats = bus['seats']
                total_avail = sum(1 for s in seats if not s['booked'])
                male_avail = sum(1 for s in seats if not s['booked'] and s['gender'] in ('male','any'))
                female_avail = sum(1 for s in seats if not s['booked'] and s['gender'] in ('female','any'))
                
                col_a, col_b, col_c = st.columns(3)
                col_a.metric("✅ Available Seats", total_avail)
                col_b.metric("👨 Male Allowed", male_avail)
                col_c.metric("👩 Female Allowed", female_avail)
                
                # Booking section
                st.subheader("🪑 Select and Book Seat")
                user_gender = st.session_state.user_gender
                
                # Create seat selection grid
                allowed_seats = [s for s in seats if not s['booked'] and 
                                (s['gender'] == user_gender or s['gender'] == 'any')]
                
                if allowed_seats:
                    # Display seat grid
                    st.write("**Available Seats:**")
                    cols_per_row = 5
                    seat_cols = st.columns(cols_per_row)
                    
                    for idx, seat in enumerate(allowed_seats):
                        col_idx = idx % cols_per_row
                        with seat_cols[col_idx]:
                            if seat['gender'] == 'male':
                                st.info(f"💺 Seat {seat['num']}\n👨 Male")
                            elif seat['gender'] == 'female':
                                st.info(f"💺 Seat {seat['num']}\n👩 Female")
                            else:
                                st.success(f"💺 Seat {seat['num']}\n⚧ Any")
                    
                    selected_seat = st.selectbox(
                        "Select seat number", 
                        [s['num'] for s in allowed_seats], 
                        key=f"seat_{bus['id']}"
                    )
                    
                    col1, col2, col3 = st.columns([1,2,1])
                    with col2:
                        if st.button(f"✅ Confirm Booking - Seat {selected_seat}", key=f"book_{bus['id']}", use_container_width=True, type="primary"):
                            # Book the seat
                            for s in seats:
                                if s['num'] == selected_seat:
                                    s['booked'] = True
                                    # Save booking
                                    booking = {
                                        "bus": bus,
                                        "seat": selected_seat,
                                        "date": st.session_state.search_criteria['date'].strftime("%Y-%m-%d")
                                    }
                                    if st.session_state.username not in st.session_state.bookings:
                                        st.session_state.bookings[st.session_state.username] = []
                                    st.session_state.bookings[st.session_state.username].append(booking)
                                    
                                    st.success(f"🎉 Seat {selected_seat} booked successfully for {user_gender} passenger!")
                                    st.balloons()
                                    st.rerun()
                else:
                    st.warning(f"⚠️ No seats available for {user_gender} passengers on this bus.")
                
                st.markdown("---")
    else:
        st.warning("😔 No buses available for the selected route on this date.")
        
        # Show alternative suggestions
        st.info("💡 **Suggestions:**")
        st.write("• Try a different travel date")
        st.write("• Check other source/destination cities")
        st.write("• Some buses operate only on specific days of the week")
        
        # Show available routes
        st.subheader("🌟 Available Routes")
        popular_routes = get_unique_routes()
        for route in popular_routes[:5]:
            st.write(f"• {route[0]} → {route[1]}")

# Reset search
if st.session_state.search_criteria["searched"]:
    if st.button("🔄 New Search", use_container_width=True):
        st.session_state.search_criteria["searched"] = False
        st.rerun()

# Footer
st.markdown("---")
st.caption("© 2025 Bus Reservation System | Book your journey with comfort and safety")