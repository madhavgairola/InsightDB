import pandas as pd
import os
import glob

class DataLoader:
    def __init__(self, data_dir='../data'):
        self.data_dir = data_dir
        self.tables = {}

    def load_data(self, data_dir=None, reset=True):
        """Loads all CSV files from the data directory into Pandas DataFrames."""
        if data_dir:
            self.data_dir = data_dir
            
        if not os.path.exists(self.data_dir):
            print(f"Data directory '{self.data_dir}' not found.")
            return self.tables

        csv_files = glob.glob(os.path.join(self.data_dir, "*.csv"))
        
        if not csv_files:
            print(f"No CSV files found in '{self.data_dir}'.")
            return self.tables

        print(f"Found {len(csv_files)} CSV files. Loading...")
        
        # Reset tables for new load
        if reset:
            self.tables = {}
        
        for file_path in csv_files:
            try:
                # Extract filename without extension as table name
                table_name = os.path.splitext(os.path.basename(file_path))[0]
                
                # Load CSV
                df = pd.read_csv(file_path)
                
                # Store in dictionary
                self.tables[table_name] = df
                print(f"Successfully loaded table: {table_name} ({len(df)} rows)")
                
            except Exception as e:
                print(f"Error loading {file_path}: {e}")

        return self.tables

    def get_table(self, table_name):
        return self.tables.get(table_name)

    def get_all_table_names(self):
        return list(self.tables.keys())

if __name__ == "__main__":
    # Test independantly
    loader = DataLoader(data_dir='./data') # Adjusted path for running directly from backend dir/root if needed
    loader.load_data()
