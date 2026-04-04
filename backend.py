# complete_bus_system_fixed.py - Fixed with proper booking display
import streamlit as st
import sqlite3
import hashlib
import pandas as pd
import numpy as np
import uuid
from datetime import datetime, timedelta
import plotly.graph_objects as go
import plotly.express as px
from sklearn.ensemble import RandomForestRegressor
from contextlib import contextmanager

# ============ DATABASE SETUP ============
DATABASE_PATH = 'bus_reservation.db'

@contextmanager
def get_db_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def init_database():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Create all tables
        cursor.execute('''CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            gender TEXT,
            email TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        
        cursor.execute('''CREATE TABLE IF NOT EXISTS buses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bus_number TEXT UNIQUE,
            name TEXT NOT NULL,
            source TEXT NOT NULL,
            destination TEXT NOT NULL,
            dep_time TEXT NOT NULL,
            arr_time TEXT NOT NULL,
            duration INTEGER,
            price REAL NOT NULL,
            total_seats INTEGER DEFAULT 40,
            bus_type TEXT DEFAULT 'Standard'
        )''')
        
        cursor.execute('''CREATE TABLE IF NOT EXISTS seats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bus_id INTEGER,
            seat_number INTEGER,
            gender_allowed TEXT,
            is_booked INTEGER DEFAULT 0,
            booked_by INTEGER,
            booking_id TEXT,
            FOREIGN KEY (bus_id) REFERENCES buses (id)
        )''')
        
        cursor.execute('''CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            booking_id TEXT UNIQUE NOT NULL,
            user_id INTEGER,
            bus_id INTEGER,
            seat_number INTEGER,
            travel_date TEXT,
            amount REAL,
            booking_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'confirmed',
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (bus_id) REFERENCES buses (id)
        )''')
        
        # Insert sample data if empty
        cursor.execute("SELECT COUNT(*) FROM users")
        if cursor.fetchone()[0] == 0:
            # Create users
            users = [
                ("admin", hash_password("admin123"), "male"),
                ("john_doe", hash_password("password123"), "male"),
                ("jane_smith", hash_password("password123"), "female"),
            ]
            for user in users:
                cursor.execute("INSERT INTO users (username, password_hash, gender) VALUES (?, ?, ?)", user)
            
            # Create buses
            buses = [
                ("BUS001", "City Express", "Mumbai", "Pune", "06:00", "10:00", 4, 450, 40, "Luxury"),
                ("BUS002", "City Express", "Mumbai", "Pune", "08:00", "12:00", 4, 450, 40, "Luxury"),
                ("BUS003", "Night Rider", "Delhi", "Jaipur", "22:30", "05:30", 7, 550, 40, "Sleeper"),
                ("BUS004", "Royal Travels", "Bangalore", "Chennai", "09:00", "15:00", 6, 600, 40, "Luxury"),
                ("BUS005", "Morning Star", "Mumbai", "Ahmedabad", "06:00", "14:00", 8, 650, 40, "Standard"),
                ("BUS006", "Coastal Express", "Chennai", "Bangalore", "20:00", "06:00", 10, 580, 40, "Sleeper"),
                ("BUS007", "Deccan Queen", "Hyderabad", "Bangalore", "07:30", "15:30", 8, 500, 40, "Luxury"),
                ("BUS008", "Gujarat Express", "Ahmedabad", "Mumbai", "21:00", "06:00", 9, 620, 40, "Sleeper"),
            ]
            
            for bus in buses:
                cursor.execute('''INSERT INTO buses 
                    (bus_number, name, source, destination, dep_time, arr_time, duration, price, total_seats, bus_type)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', bus)
                bus_id = cursor.lastrowid
                
                # Create 40 seats per bus
                for seat_num in range(1, 41):
                    if seat_num <= 20:
                        gender = "male"
                    elif seat_num <= 30:
                        gender = "female"
                    else:
                        gender = "any"
                    
                    # Initially no seats are booked
                    is_booked = 0
                    
                    cursor.execute('''INSERT INTO seats 
                        (bus_id, seat_number, gender_allowed, is_booked)
                        VALUES (?, ?, ?, ?)''', (bus_id, seat_num, gender, is_booked))
    
    print("✅ Database initialized!")

# ============ MACHINE LEARNING MODEL ============
class DemandPredictor:
    def __init__(self):
        self.model = RandomForestRegressor(n_estimators=50, random_state=42)
        self.is_trained = False
        
    def train(self):
        # Generate training data
        data = []
        for _ in range(2000):
            day = np.random.randint(0, 7)
            month = np.random.randint(1, 13)
            price = np.random.randint(300, 800)
            is_weekend = 1 if day >= 5 else 0
            is_holiday = 1 if np.random.random() < 0.05 else 0
            is_peak = 1 if month in [5, 6, 12] else 0
            
            demand = 50 + (is_weekend * 20) + (is_peak * 15) + (is_holiday * 25)
            demand += np.random.normal(0, 10)
            demand = max(0, min(100, demand))
            
            data.append([day, month, price, is_weekend, is_holiday, demand])
        
        df = pd.DataFrame(data, columns=['day', 'month', 'price', 'is_weekend', 'is_holiday', 'demand'])
        X = df[['day', 'month', 'price', 'is_weekend', 'is_holiday']]
        y = df['demand']
        
        self.model.fit(X, y)
        self.is_trained = True
    
    def predict(self, travel_date, price):
        if not self.is_trained:
            self.train()
        
        travel_date = datetime.strptime(travel_date, '%Y-%m-%d') if isinstance(travel_date, str) else travel_date
        
        features = np.array([[
            travel_date.weekday(),
            travel_date.month,
            price,
            1 if travel_date.weekday() >= 5 else 0,
            1 if travel_date.strftime('%m-%d') in ['01-26', '08-15', '10-02', '12-25'] else 0
        ]])
        
        demand = self.model.predict(features)[0]
        return round(max(0, min(100, demand)), 1)

def optimize_price(base_price, demand, days_left):
    multiplier = 1.0
    if demand > 80:
        multiplier = 1.3
    elif demand > 60:
        multiplier = 1.15
    elif demand > 40:
        multiplier = 1.0
    elif demand > 20:
        multiplier = 0.9
    else:
        multiplier = 0.8
    
    if days_left <= 1:
        multiplier *= 1.3
    elif days_left <= 3:
        multiplier *= 1.15
    elif days_left >= 14:
        multiplier *= 0.85
    
    return round(base_price * multiplier, 2)

# ============ DATABASE FUNCTIONS ============
def authenticate_user(username, password):
    password_hash = hash_password(password)
    with get_db_connection() as conn:
        user = conn.execute(
            "SELECT id, username, gender FROM users WHERE username = ? AND password_hash = ?",
            (username, password_hash)
        ).fetchone()
        return dict(user) if user else None

def create_user(username, password, gender):
    password_hash = hash_password(password)
    with get_db_connection() as conn:
        try:
            conn.execute("INSERT INTO users (username, password_hash, gender) VALUES (?, ?, ?)",
                        (username, password_hash, gender))
            return True
        except:
            return False

def search_buses(source, destination):
    with get_db_connection() as conn:
        buses = conn.execute(
            """SELECT b.*, 
               (SELECT COUNT(*) FROM seats WHERE bus_id = b.id AND is_booked = 0) as available_seats,
               (SELECT COUNT(*) FROM seats WHERE bus_id = b.id AND is_booked = 1) as booked_seats
               FROM buses b WHERE b.source = ? AND b.destination = ?""",
            (source, destination)
        ).fetchall()
        
        result = []
        for bus in buses:
            bus_dict = dict(bus)
            seats = conn.execute(
                "SELECT seat_number, gender_allowed, is_booked FROM seats WHERE bus_id = ? ORDER BY seat_number",
                (bus['id'],)
            ).fetchall()
            bus_dict['seats'] = [dict(seat) for seat in seats]
            result.append(bus_dict)
        
        return result

def get_seat_stats(bus_id):
    with get_db_connection() as conn:
        seats = conn.execute(
            "SELECT seat_number, gender_allowed, is_booked FROM seats WHERE bus_id = ?",
            (bus_id,)
        ).fetchall()
        
        total = len(seats)
        booked = sum(1 for s in seats if s['is_booked'] == 1)
        available = total - booked
        
        male_total = sum(1 for s in seats if s['gender_allowed'] == 'male')
        male_booked = sum(1 for s in seats if s['gender_allowed'] == 'male' and s['is_booked'] == 1)
        male_available = male_total - male_booked
        
        female_total = sum(1 for s in seats if s['gender_allowed'] == 'female')
        female_booked = sum(1 for s in seats if s['gender_allowed'] == 'female' and s['is_booked'] == 1)
        female_available = female_total - female_booked
        
        any_total = sum(1 for s in seats if s['gender_allowed'] == 'any')
        any_booked = sum(1 for s in seats if s['gender_allowed'] == 'any' and s['is_booked'] == 1)
        any_available = any_total - any_booked
        
        return {
            'total_seats': total,
            'booked_seats': booked,
            'available_seats': available,
            'occupancy_rate': round((booked / total) * 100, 1) if total > 0 else 0,
            'male': {'total': male_total, 'booked': male_booked, 'available': male_available},
            'female': {'total': female_total, 'booked': female_booked, 'available': female_available},
            'any': {'total': any_total, 'booked': any_booked, 'available': any_available},
            'seats': [dict(seat) for seat in seats]
        }

def book_ticket(user_id, bus_id, seat_number, travel_date, amount):
    booking_id = str(uuid.uuid4())[:8].upper()
    
    with get_db_connection() as conn:
        # Check if seat is available
        seat = conn.execute(
            "SELECT is_booked FROM seats WHERE bus_id = ? AND seat_number = ?",
            (bus_id, seat_number)
        ).fetchone()
        
        if not seat or seat['is_booked'] == 1:
            return None
        
        # Book the seat
        conn.execute(
            "UPDATE seats SET is_booked = 1, booked_by = ?, booking_id = ? WHERE bus_id = ? AND seat_number = ?",
            (user_id, booking_id, bus_id, seat_number)
        )
        
        # Create booking record
        conn.execute(
            """INSERT INTO bookings (booking_id, user_id, bus_id, seat_number, travel_date, amount, status) 
               VALUES (?, ?, ?, ?, ?, ?, 'confirmed')""",
            (booking_id, user_id, bus_id, seat_number, travel_date, amount)
        )
        
        return booking_id

def get_user_bookings(user_id):
    with get_db_connection() as conn:
        bookings = conn.execute('''
            SELECT b.*, bs.name as bus_name, bs.source, bs.destination, bs.dep_time, bs.arr_time, bs.price as bus_price
            FROM bookings b
            JOIN buses bs ON b.bus_id = bs.id
            WHERE b.user_id = ? AND b.status = 'confirmed'
            ORDER BY b.booking_date DESC
        ''', (user_id,)).fetchall()
        
        result = []
        for booking in bookings:
            result.append(dict(booking))
        return result

def cancel_booking(booking_id, bus_id, seat_number):
    with get_db_connection() as conn:
        # Update seat status
        conn.execute("UPDATE seats SET is_booked = 0, booked_by = NULL, booking_id = NULL WHERE bus_id = ? AND seat_number = ?",
                    (bus_id, seat_number))
        # Update booking status
        conn.execute("UPDATE bookings SET status = 'cancelled' WHERE booking_id = ?", (booking_id,))
        return True

def get_all_cities():
    with get_db_connection() as conn:
        cities = conn.execute(
            "SELECT DISTINCT source as city FROM buses UNION SELECT DISTINCT destination FROM buses ORDER BY city"
        ).fetchall()
        return [city['city'] for city in cities]

def get_system_stats():
    with get_db_connection() as conn:
        total_buses = conn.execute("SELECT COUNT(*) as count FROM buses").fetchone()['count']
        total_seats = conn.execute("SELECT COUNT(*) as count FROM seats").fetchone()['count']
        booked_seats = conn.execute("SELECT COUNT(*) as count FROM seats WHERE is_booked = 1").fetchone()['count']
        total_bookings = conn.execute("SELECT COUNT(*) as count FROM bookings WHERE status = 'confirmed'").fetchone()['count']
        total_revenue = conn.execute("SELECT SUM(amount) as total FROM bookings WHERE status = 'confirmed'").fetchone()['total'] or 0
        
        return {
            'total_buses': total_buses,
            'total_seats': total_seats,
            'booked_seats': booked_seats,
            'available_seats': total_seats - booked_seats,
            'occupancy_rate': round((booked_seats / total_seats) * 100, 1) if total_seats > 0 else 0,
            'total_bookings': total_bookings,
            'total_revenue': total_revenue
        }

# ============ UI COMPONENTS ============
def display_seat_availability(bus_id, unique_key):
    """Display seat availability with full clarity"""
    stats = get_seat_stats(bus_id)
    
    st.subheader("📊 Seat Availability Summary")
    
    # Main metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Seats", stats['total_seats'])
    with col2:
        st.metric("🟢 Available", stats['available_seats'])
    with col3:
        st.metric("🔴 Booked", stats['booked_seats'])
    with col4:
        st.metric("📈 Occupancy", f"{stats['occupancy_rate']}%")
    
    st.progress(stats['occupancy_rate'] / 100, text=f"Bus Occupancy: {stats['occupancy_rate']}%")
    
    # Gender-wise breakdown
    st.subheader("👥 Gender-wise Seat Breakdown")
    
    gender_col1, gender_col2, gender_col3 = st.columns(3)
    
    with gender_col1:
        st.markdown("**👨 Male Seats**")
        st.write(f"Total: {stats['male']['total']}")
        st.write(f"🟢 Available: {stats['male']['available']}")
        st.write(f"🔴 Booked: {stats['male']['booked']}")
    
    with gender_col2:
        st.markdown("**👩 Female Seats**")
        st.write(f"Total: {stats['female']['total']}")
        st.write(f"🟢 Available: {stats['female']['available']}")
        st.write(f"🔴 Booked: {stats['female']['booked']}")
    
    with gender_col3:
        st.markdown("**⚧ Any Gender Seats**")
        st.write(f"Total: {stats['any']['total']}")
        st.write(f"🟢 Available: {stats['any']['available']}")
        st.write(f"🔴 Booked: {stats['any']['booked']}")
    
    # Visual seat map
    st.subheader("🪑 Seat Map (40 Seats)")
    
    # Create a visual grid of seats
    seats = stats['seats']
    cols_per_row = 8
    
    # Legend
    leg_col1, leg_col2, leg_col3, leg_col4 = st.columns(4)
    with leg_col1:
        st.markdown("🟢 **Available for you**")
    with leg_col2:
        st.markdown("🔵 **Available (other gender)**")
    with leg_col3:
        st.markdown("🔴 **Booked**")
    with leg_col4:
        st.markdown("⚪ **Not for your gender**")
    
    st.markdown("---")
    
    # Display seats in grid
    user_gender = st.session_state.user_gender
    
    for row in range(0, len(seats), cols_per_row):
        cols = st.columns(cols_per_row)
        row_seats = seats[row:row+cols_per_row]
        
        for idx, seat in enumerate(row_seats):
            with cols[idx]:
                if seat['is_booked'] == 1:
                    st.error(f"🔴 {seat['seat_number']}")
                else:
                    if seat['gender_allowed'] == user_gender:
                        st.success(f"🟢 {seat['seat_number']}")
                    elif seat['gender_allowed'] == 'any':
                        st.success(f"🟢 {seat['seat_number']}")
                    else:
                        st.info(f"🔵 {seat['seat_number']}")
    
    return stats

# ============ STREAMLIT UI ============
st.set_page_config(page_title="Bus Reservation System", page_icon="🚌", layout="wide")

# Custom CSS
st.markdown("""
<style>
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 0.5rem 1rem;
        border-radius: 8px;
        width: 100%;
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        transition: 0.3s;
    }
    .success-box {
        background: linear-gradient(135deg, #84fab0 0%, #8fd3f4 100%);
        padding: 1rem;
        border-radius: 10px;
        text-align: center;
    }
    .booking-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        margin: 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Initialize
init_database()
demand_predictor = DemandPredictor()
demand_predictor.train()

# Session state
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.user_id = None
    st.session_state.user_gender = "male"

# ============ LOGIN PAGE ============
if not st.session_state.logged_in:
    st.title("🚌 Bus Reservation System")
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🔐 Login")
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login")
            
            if submitted:
                user = authenticate_user(username, password)
                if user:
                    st.session_state.logged_in = True
                    st.session_state.username = user['username']
                    st.session_state.user_id = user['id']
                    st.session_state.user_gender = user['gender']
                    st.rerun()
                else:
                    st.error("❌ Invalid credentials! Try: admin / admin123")
    
    with col2:
        st.subheader("📝 Sign Up")
        with st.form("signup_form"):
            new_user = st.text_input("Username")
            new_pass = st.text_input("Password", type="password")
            confirm_pass = st.text_input("Confirm Password", type="password")
            gender = st.selectbox("Gender", ["male", "female"])
            submitted = st.form_submit_button("Sign Up")
            
            if submitted:
                if new_pass != confirm_pass:
                    st.error("Passwords don't match!")
                elif len(new_user) < 3:
                    st.error("Username must be at least 3 characters")
                elif create_user(new_user, new_pass, gender):
                    st.success("Account created! Please login.")
                else:
                    st.error("Username already exists!")
    
    st.info("💡 **Demo Credentials:** Username: `admin`, Password: `admin123`")
    st.stop()

# ============ MAIN APP ============
# Sidebar
st.sidebar.title(f"👋 Welcome, {st.session_state.username}")
st.sidebar.markdown(f"**Gender:** {st.session_state.user_gender.capitalize()}")
st.sidebar.markdown("---")

menu = st.sidebar.radio("📌 Navigation", [
    "🔍 Search & Book",
    "📋 My Bookings",
    "📊 System Dashboard",
    "📈 Seat Availability Report"
])

st.sidebar.markdown("---")
if st.sidebar.button("🚪 Logout"):
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

# ============ SEARCH & BOOK PAGE ============
if menu == "🔍 Search & Book":
    st.title("🔍 Search & Book Your Journey")
    
    col1, col2, col3 = st.columns(3)
    
    cities = get_all_cities()
    
    with col1:
        source = st.selectbox("From 🏁", cities)
    with col2:
        dest_options = [c for c in cities if c != source]
        destination = st.selectbox("To 🏁", dest_options)
    with col3:
        travel_date = st.date_input(
            "Travel Date 📅",
            min_value=datetime.now().date(),
            max_value=datetime.now().date() + timedelta(days=30)
        )
    
    if st.button("🔍 Search Buses", type="primary"):
        with st.spinner("Searching buses..."):
            buses = search_buses(source, destination)
        
        if buses:
            st.success(f"✅ Found {len(buses)} buses")
            
            for idx, bus in enumerate(buses):
                days_left = max(0, (travel_date - datetime.now().date()).days)
                predicted_demand = demand_predictor.predict(travel_date.strftime("%Y-%m-%d"), bus['price'])
                optimized_price = optimize_price(bus['price'], predicted_demand, days_left)
                
                with st.expander(f"🚌 {bus['name']} | {bus['dep_time']} - {bus['arr_time']} | ₹{bus['price']}", expanded=True):
                    
                    # Bus details
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Departure", bus['dep_time'])
                    with col2:
                        st.metric("Arrival", bus['arr_time'])
                    with col3:
                        st.metric("Available Seats", bus['available_seats'])
                    with col4:
                        st.metric("Bus Type", bus['bus_type'])
                    
                    # AI Insights
                    st.markdown("---")
                    st.subheader("🤖 AI Insights")
                    
                    ai_col1, ai_col2, ai_col3 = st.columns(3)
                    with ai_col1:
                        demand_level = "🔥 High" if predicted_demand > 70 else ("📊 Medium" if predicted_demand > 40 else "❄️ Low")
                        st.info(f"**Predicted Demand:** {predicted_demand}%\n{demand_level}")
                    with ai_col2:
                        price_diff = optimized_price - bus['price']
                        price_icon = "⬆️" if price_diff > 0 else "⬇️"
                        st.info(f"**AI Optimized Price:** ₹{optimized_price}\n{price_icon} ₹{abs(price_diff)} from base")
                    with ai_col3:
                        st.info(f"**Days to Travel:** {days_left} days\n{'Early bird available' if days_left > 7 else 'Last minute booking'}")
                    
                    # Seat Availability Display
                    st.markdown("---")
                    seat_stats = display_seat_availability(bus['id'], f"bus_{bus['id']}_{idx}")
                    
                    # Booking Section
                    st.markdown("---")
                    st.subheader("🎫 Book Your Ticket")
                    
                    user_gender = st.session_state.user_gender
                    available_for_user = [
                        s for s in seat_stats['seats'] 
                        if s['is_booked'] == 0 and (s['gender_allowed'] == user_gender or s['gender_allowed'] == 'any')
                    ]
                    
                    if available_for_user:
                        seat_numbers = [s['seat_number'] for s in available_for_user]
                        selected_seat = st.selectbox("Select Seat Number", seat_numbers, key=f"seat_select_{bus['id']}_{idx}")
                        
                        col1, col2, col3 = st.columns([1, 2, 1])
                        with col2:
                            if st.button(f"✅ Confirm Booking - Seat {selected_seat}", key=f"book_btn_{bus['id']}_{idx}", type="primary"):
                                booking_id = book_ticket(
                                    st.session_state.user_id,
                                    bus['id'],
                                    selected_seat,
                                    travel_date.strftime("%Y-%m-%d"),
                                    optimized_price
                                )
                                
                                if booking_id:
                                    st.balloons()
                                    st.markdown(f"""
                                    <div class="success-box">
                                        <h2>🎉 Booking Confirmed!</h2>
                                        <p><strong>Booking ID:</strong> {booking_id}</p>
                                        <p><strong>Bus:</strong> {bus['name']}</p>
                                        <p><strong>Route:</strong> {bus['source']} → {bus['destination']}</p>
                                        <p><strong>Seat Number:</strong> {selected_seat}</p>
                                        <p><strong>Travel Date:</strong> {travel_date.strftime('%Y-%m-%d')}</p>
                                        <p><strong>Departure:</strong> {bus['dep_time']}</p>
                                        <p><strong>Arrival:</strong> {bus['arr_time']}</p>
                                        <p><strong>Amount Paid:</strong> ₹{optimized_price}</p>
                                    </div>
                                    """, unsafe_allow_html=True)
                                    st.rerun()
                                else:
                                    st.error("❌ Booking failed! Seat may have been taken.")
                    else:
                        st.warning(f"⚠️ No seats available for {user_gender} passengers")
        else:
            st.warning("😔 No buses found for this route")

# ============ MY BOOKINGS PAGE ============
elif menu == "📋 My Bookings":
    st.title("📋 My Bookings")
    
    bookings = get_user_bookings(st.session_state.user_id)
    
    if bookings:
        st.success(f"✨ You have {len(bookings)} confirmed booking(s)")
        
        for idx, booking in enumerate(bookings):
            # Create a nice card for each booking
            st.markdown(f"""
            <div class="booking-card">
                <h3>🎫 {booking['booking_id']}</h3>
                <hr style="margin: 10px 0; border-color: rgba(255,255,255,0.3);">
                <table style="width: 100%; color: white;">
                    <tr>
                        <td><strong>🚌 Bus:</strong></td>
                        <td>{booking['bus_name']}</td>
                        <td><strong>💺 Seat:</strong></td>
                        <td>{booking['seat_number']}</td>
                    </tr>
                    <tr>
                        <td><strong>📍 Route:</strong></td>
                        <td>{booking['source']} → {booking['destination']}</td>
                        <td><strong>📅 Date:</strong></td>
                        <td>{booking['travel_date']}</td>
                    </tr>
                    <tr>
                        <td><strong>⏰ Time:</strong></td>
                        <td>{booking['dep_time']} - {booking['arr_time']}</td>
                        <td><strong>💰 Amount:</strong></td>
                        <td>₹{booking['amount']}</td>
                    </tr>
                    <tr>
                        <td><strong>📆 Booked On:</strong></td>
                        <td colspan="3">{booking['booking_date']}</td>
                    </tr>
                </table>
            </div>
            <br>
            """, unsafe_allow_html=True)
            
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                if st.button(f"❌ Cancel Booking", key=f"cancel_{booking['booking_id']}_{idx}"):
                    if cancel_booking(booking['booking_id'], booking['bus_id'], booking['seat_number']):
                        st.success("✅ Booking cancelled successfully!")
                        st.rerun()
            
            st.markdown("---")
    else:
        st.info("📭 No bookings found. Search and book your first journey!")
        st.markdown("""
        <div style="text-align: center; padding: 2rem;">
            <h3>How to Book a Ticket?</h3>
            <p>1. Go to <strong>Search & Book</strong> page</p>
            <p>2. Select source and destination cities</p>
            <p>3. Choose travel date</p>
            <p>4. Click Search Buses</p>
            <p>5. Select a bus and choose your seat</p>
            <p>6. Click Confirm Booking</p>
        </div>
        """, unsafe_allow_html=True)

# ============ SYSTEM DASHBOARD ============
elif menu == "📊 System Dashboard":
    st.title("📊 System Dashboard")
    
    stats = get_system_stats()
    
    # Key metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Buses", stats['total_buses'])
    with col2:
        st.metric("Total Seats", stats['total_seats'])
    with col3:
        st.metric("Total Bookings", stats['total_bookings'])
    with col4:
        st.metric("Total Revenue", f"₹{stats['total_revenue']:,.0f}")
    
    # Occupancy metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Booked Seats", stats['booked_seats'])
    with col2:
        st.metric("Available Seats", stats['available_seats'])
    with col3:
        st.metric("Overall Occupancy", f"{stats['occupancy_rate']}%")
    
    st.progress(stats['occupancy_rate'] / 100, text=f"System-wide Occupancy: {stats['occupancy_rate']}%")
    
    # Occupancy Gauge Chart
    fig = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = stats['occupancy_rate'],
        title = {'text': "System Occupancy Rate"},
        gauge = {
            'axis': {'range': [None, 100]},
            'bar': {'color': "#667eea"},
            'steps': [
                {'range': [0, 30], 'color': "lightgray"},
                {'range': [30, 70], 'color': "gray"},
                {'range': [70, 100], 'color': "darkgray"}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': 90
            }
        }
    ))
    fig.update_layout(height=300)
    st.plotly_chart(fig, use_container_width=True, key="occupancy_gauge_chart")

# ============ SEAT AVAILABILITY REPORT ============
elif menu == "📈 Seat Availability Report":
    st.title("📈 Complete Seat Availability Report")
    
    with get_db_connection() as conn:
        buses = conn.execute("SELECT id, name, source, destination FROM buses").fetchall()
    
    # Overall stats
    total_seats = 0
    total_booked = 0
    
    for bus in buses:
        stats = get_seat_stats(bus['id'])
        total_seats += stats['total_seats']
        total_booked += stats['booked_seats']
    
    overall_occupancy = (total_booked / total_seats) * 100 if total_seats > 0 else 0
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Buses", len(buses))
    with col2:
        st.metric("Total Seats", total_seats)
    with col3:
        st.metric("Overall Occupancy", f"{overall_occupancy:.1f}%")
    
    st.progress(overall_occupancy / 100)
    
    # Bus-wise report
    st.subheader("Bus-wise Seat Availability")
    
    report_data = []
    for bus in buses:
        stats = get_seat_stats(bus['id'])
        report_data.append({
            'Bus Name': bus['name'],
            'Route': f"{bus['source']} → {bus['destination']}",
            'Total Seats': stats['total_seats'],
            'Booked': stats['booked_seats'],
            'Available': stats['available_seats'],
            'Occupancy': f"{stats['occupancy_rate']}%"
        })
    
    df = pd.DataFrame(report_data)
    st.dataframe(df, use_container_width=True, hide_index=True)
    
    # Bar chart
    fig = px.bar(df, x='Bus Name', y=[float(x.replace('%', '')) for x in df['Occupancy']],
                 title="Bus Occupancy Comparison",
                 labels={'y': 'Occupancy (%)', 'x': 'Bus'},
                 color=[float(x.replace('%', '')) for x in df['Occupancy']],
                 color_continuous_scale='Viridis')
    st.plotly_chart(fig, use_container_width=True, key="occupancy_bar_chart")
    
    # Detailed report for each bus
    st.subheader("Detailed Bus Reports")
    for idx, bus in enumerate(buses):
        with st.expander(f"🚌 {bus['name']} - {bus['source']} to {bus['destination']}"):
            display_seat_availability(bus['id'], f"report_{bus['id']}_{idx}")

# Footer
st.markdown("---")
st.caption("🚌 Bus Reservation System | Machine Learning")