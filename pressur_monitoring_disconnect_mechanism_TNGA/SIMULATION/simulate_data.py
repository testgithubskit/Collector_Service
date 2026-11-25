import pandas as pd
import pyodbc
import time
import random
from datetime import datetime, timedelta
import threading
import signal
import sys

class DataSimulator:
    def __init__(self):
        self.running = False
        self.file_path = r"G:\GOKUL\TOYOTA\Collector_1\DATA.xlsx"
        self.conn = None
        self.cursor = None
        self.data = None
        self.current_index = 0
        
    def load_data(self):
        """Load Excel data"""
        try:
            df = pd.read_excel(self.file_path, engine="openpyxl", header=1)
            df.columns = df.columns.str.strip().str.lower()
            
            # Convert timestamp to datetime
            df['timestamp_timezone'] = pd.to_datetime(df['timestamp_timezone'])
            
            # Sort by timestamp to maintain chronological order
            df = df.sort_values('timestamp_timezone').reset_index(drop=True)
            
            self.data = df
            print(f"✅ Loaded {len(df)} records from Excel file")
            print(f"📅 Time range: {df['timestamp_timezone'].min()} to {df['timestamp_timezone'].max()}")
            
        except Exception as e:
            print(f"❌ Error loading data: {e}")
            raise
    
    def connect_to_db(self):
        """Connect to SQL Server"""
        try:
            self.conn = pyodbc.connect(
                "DRIVER={ODBC Driver 17 for SQL Server};"
                "SERVER=localhost\\SQLEXPRESS;"
                "DATABASE=Machine_DB;"
                "Trusted_Connection=yes;"
            )
            self.cursor = self.conn.cursor()
            print("✅ Connected to SQL Server")
            
        except Exception as e:
            print(f"❌ Error connecting to database: {e}")
            raise
    
    def calculate_wait_time(self, current_row, next_row):
        """Calculate wait time between rows based on timestamp difference"""
        if next_row is None:
            return 1.0  # Default 1 second if no next row
        
        time_diff = next_row['timestamp_timezone'] - current_row['timestamp_timezone']
        # Convert to seconds for real-time simulation
        wait_seconds = time_diff.total_seconds()
        
        # Ensure minimum wait time of 0.5 seconds and maximum of 10 seconds
        return max(0.5, min(wait_seconds, 10.0))
    
    def insert_data(self, row, current_time):
        """Insert a single row into database with current timestamp"""
        try:
            # Use current time instead of original timestamp for real-time simulation
            insert_query = """
            INSERT INTO MCT_Data 
            (machine_number, timestamp_timezone, cycle_time, model, counter)
            VALUES (?, ?, ?, ?, ?)
            """
            
            self.cursor.execute(insert_query,
                str(row['machine_number']),
                current_time,  # Use current time
                float(row['cycle_time']),
                int(row['model']),
                int(row['counter'])
            )
            
            self.conn.commit()
            print(f"📊 Inserted: {row['machine_number']} at {current_time}")
            
        except Exception as e:
            print(f"❌ Error inserting data: {e}")
            self.conn.rollback()
    
    def simulate_continuous(self):
        """Main simulation loop"""
        print("🚀 Starting continuous data simulation...")
        print("📝 Press Ctrl+C to stop")
        
        start_time = datetime.now()
        
        try:
            while self.running and self.current_index < len(self.data):
                current_row = self.data.iloc[self.current_index]
                
                # Calculate current time based on simulation start
                elapsed = datetime.now() - start_time
                current_time = start_time + elapsed
                
                # Insert current row
                self.insert_data(current_row, current_time)
                
                # Get next row for wait time calculation
                next_row = None
                if self.current_index < len(self.data) - 1:
                    next_row = self.data.iloc[self.current_index + 1]
                
                # Calculate wait time
                wait_time = self.calculate_wait_time(current_row, next_row)
                
                print(f"⏱️ Waiting {wait_time:.2f} seconds...")
                time.sleep(wait_time)
                
                self.current_index += 1
                
                # Optional: Loop back to beginning when reaching end
                if self.current_index >= len(self.data):
                    print("🔄 Reached end of data, starting from beginning...")
                    self.current_index = 0
                    
        except KeyboardInterrupt:
            print("\n⏹️ Simulation stopped by user")
        except Exception as e:
            print(f"❌ Simulation error: {e}")
        finally:
            self.running = False
    
    def start_simulation(self):
        """Start the continuous simulation"""
        try:
            self.load_data()
            self.connect_to_db()
            self.running = True
            self.simulate_continuous()
                
        except Exception as e:
            print(f"❌ Failed to start simulation: {e}")
        finally:
            self.cleanup()
    
    def simulate_batch(self):
        """Simulate all data quickly (for testing)"""
        print("⚡ Running batch simulation...")
        
        for index, row in self.data.iterrows():
            current_time = datetime.now()
            self.insert_data(row, current_time)
            time.sleep(0.01)  # Small delay between inserts
        
        print(f"✅ Batch simulation completed: {len(self.data)} records inserted")
    
    def cleanup(self):
        """Clean up resources"""
        self.running = False
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        print("🔌 Database connections closed")

def signal_handler(sig, frame):
    """Handle Ctrl+C"""
    print('\n⏹️ Stopping simulation...')
    sys.exit(0)

if __name__ == "__main__":
    # Register signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    
    simulator = DataSimulator()
    print("🚀 Starting real-time data simulation based on Excel timing patterns...")
    print("📝 Press Ctrl+C to stop")
    simulator.start_simulation()
