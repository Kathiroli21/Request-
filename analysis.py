import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

class PunchDataAnalyzer:
    def __init__(self, punch_in_file, punch_out_file):
        """
        Initialize the analyzer with punch in and punch out data files
        
        Parameters:
        punch_in_file: Path to Excel file with punch in data
        punch_out_file: Path to Excel file with punch out data
        """
        self.punch_in_file = punch_in_file
        self.punch_out_file = punch_out_file
        self.punch_in_df = None
        self.punch_out_df = None
        self.merged_df = None
        
    def load_data(self):
        """Load punch in and punch out data from Excel files"""
        try:
            # Load punch in data
            self.punch_in_df = pd.read_excel(self.punch_in_file)
            print(f"Loaded {len(self.punch_in_df)} punch in records")
            
            # Load punch out data  
            self.punch_out_df = pd.read_excel(self.punch_out_file)
            print(f"Loaded {len(self.punch_out_df)} punch out records")
            
            return True
        except Exception as e:
            print(f"Error loading data: {e}")
            return False
    
    def clean_and_prepare_data(self):
        """Clean and prepare data for analysis"""
        
        # Clean punch in data
        punch_in_clean = self.punch_in_df.copy()
        
        # Rename columns for consistency (adjust these based on your actual column names)
        punch_in_clean.columns = ['persno', 'in_date', 'punchinsec', 'tm_ev_type_in', 'punchin_time', 'emp_date_key']
        
        # Convert date and time columns
        punch_in_clean['in_date'] = pd.to_datetime(punch_in_clean['in_date'])
        punch_in_clean['punchin_time'] = pd.to_datetime(punch_in_clean['punchin_time'], format='%H:%M:%S', errors='coerce').dt.time
        
        # Create datetime combination for punch in
        punch_in_clean['punch_in_datetime'] = pd.to_datetime(
            punch_in_clean['in_date'].dt.strftime('%Y-%m-%d') + ' ' + 
            punch_in_clean['punchin_time'].astype(str)
        )
        
        # Clean punch out data
        punch_out_clean = self.punch_out_df.copy()
        
        # Rename columns (adjust these based on your actual column names)
        punch_out_clean.columns = ['emp_date_key', 'punch_out_sec', 'persno', 'tm_ev_type_out', 'out_date', 'punch_out_time']
        
        # Convert date and time columns
        punch_out_clean['out_date'] = pd.to_datetime(punch_out_clean['out_date'])
        punch_out_clean['punch_out_time'] = pd.to_datetime(punch_out_clean['punch_out_time'], format='%H:%M:%S', errors='coerce').dt.time
        
        # Create datetime combination for punch out
        punch_out_clean['punch_out_datetime'] = pd.to_datetime(
            punch_out_clean['out_date'].dt.strftime('%Y-%m-%d') + ' ' + 
            punch_out_clean['punch_out_time'].astype(str)
        )
        
        self.punch_in_df = punch_in_clean
        self.punch_out_df = punch_out_clean
        
        print("Data cleaning completed")
    
    def handle_overnight_shifts(self):
        """Handle overnight shift scenarios where punch out is next day"""
        
        # Create a copy for overnight handling
        punch_out_overnight = self.punch_out_df.copy()
        
        # For each punch out, check if there's a corresponding punch in from previous day
        for idx, row in punch_out_overnight.iterrows():
            persno = row['persno']
            punch_out_time = row['punch_out_datetime']
            
            # Look for punch in from the same day first
            same_day_punch_in = self.punch_in_df[
                (self.punch_in_df['persno'] == persno) & 
                (self.punch_in_df['in_date'].dt.date == punch_out_time.date())
            ]
            
            # If no same day punch in found, check previous day for late night punch ins
            if len(same_day_punch_in) == 0:
                prev_day = punch_out_time.date() - timedelta(days=1)
                prev_day_punch_in = self.punch_in_df[
                    (self.punch_in_df['persno'] == persno) & 
                    (self.punch_in_df['in_date'].dt.date == prev_day) &
                    (self.punch_in_df['punch_in_datetime'].dt.hour >= 20)  # Late night punch ins (after 8 PM)
                ]
                
                if len(prev_day_punch_in) > 0:
                    print(f"Overnight shift detected for person {persno}: Punch in on {prev_day}, Punch out on {punch_out_time.date()}")
        
        return punch_out_overnight
    
    def merge_punch_data(self):
        """Merge punch in and punch out data with overnight shift handling"""
        
        # Handle overnight shifts
        punch_out_processed = self.handle_overnight_shifts()
        
        # Strategy 1: Match on same date first
        merged_same_day = pd.merge(
            self.punch_in_df,
            punch_out_processed,
            on=['persno'],
            how='outer',
            suffixes=('_in', '_out')
        )
        
        # Filter for same day matches
        merged_same_day['same_day'] = (
            merged_same_day['in_date'].dt.date == merged_same_day['out_date'].dt.date
        )
        
        # Strategy 2: Handle overnight shifts (punch in late, punch out next day early)
        overnight_matches = []
        
        for idx, row in merged_same_day.iterrows():
            if pd.isna(row['same_day']) or not row['same_day']:
                persno = row['persno']
                
                if not pd.isna(row['punch_in_datetime']) and pd.isna(row['punch_out_datetime']):
                    # Look for punch out next day for late punch ins
                    if row['punch_in_datetime'].hour >= 20:  # Late punch in
                        next_day = row['in_date'].date() + timedelta(days=1)
                        next_day_punch_out = punch_out_processed[
                            (punch_out_processed['persno'] == persno) & 
                            (punch_out_processed['out_date'].dt.date == next_day) &
                            (punch_out_processed['punch_out_datetime'].dt.hour <= 10)  # Early punch out
                        ]
                        
                        if len(next_day_punch_out) > 0:
                            overnight_matches.append({
                                'persno': persno,
                                'punch_in_datetime': row['punch_in_datetime'],
                                'punch_out_datetime': next_day_punch_out.iloc[0]['punch_out_datetime'],
                                'shift_type': 'overnight'
                            })
        
        self.merged_df = merged_same_day
        self.overnight_matches = overnight_matches
        
        print(f"Found {len(overnight_matches)} overnight shift matches")
    
    def analyze_punch_patterns(self):
        """Perform the main analysis"""
        
        results = {}
        
        # 1. Punch in without punch out
        punch_in_only = self.merged_df[
            (~pd.isna(self.merged_df['punch_in_datetime'])) & 
            (pd.isna(self.merged_df['punch_out_datetime']))
        ]
        results['punch_in_only'] = punch_in_only[['persno', 'in_date', 'punchin_time', 'punch_in_datetime']]
        
        # 2. Punch out without punch in
        punch_out_only = self.merged_df[
            (pd.isna(self.merged_df['punch_in_datetime'])) & 
            (~pd.isna(self.merged_df['punch_out_datetime']))
        ]
        results['punch_out_only'] = punch_out_only[['persno', 'out_date', 'punch_out_time', 'punch_out_datetime']]
        
        # 3. Both punch in and punch out (complete records)
        complete_punches = self.merged_df[
            (~pd.isna(self.merged_df['punch_in_datetime'])) & 
            (~pd.isna(self.merged_df['punch_out_datetime']))
        ]
        results['complete_punches'] = complete_punches[['persno', 'in_date', 'punchin_time', 'out_date', 'punch_out_time', 'punch_in_datetime', 'punch_out_datetime']]
        
        # 4. Add overnight shifts to complete punches
        if hasattr(self, 'overnight_matches') and self.overnight_matches:
            overnight_df = pd.DataFrame(self.overnight_matches)
            results['overnight_shifts'] = overnight_df
        
        return results
    
    def generate_report(self, results):
        """Generate analysis report"""
        
        print("\n" + "="*60)
        print("PUNCH DATA ANALYSIS REPORT")
        print("="*60)
        
        print(f"\n1. PUNCH IN WITHOUT PUNCH OUT: {len(results['punch_in_only'])} records")
        if len(results['punch_in_only']) > 0:
            print(results['punch_in_only'].head(10))
        
        print(f"\n2. PUNCH OUT WITHOUT PUNCH IN: {len(results['punch_out_only'])} records")
        if len(results['punch_out_only']) > 0:
            print(results['punch_out_only'].head(10))
        
        print(f"\n3. COMPLETE PUNCHES (IN + OUT): {len(results['complete_punches'])} records")
        if len(results['complete_punches']) > 0:
            print(results['complete_punches'].head(10))
        
        if 'overnight_shifts' in results:
            print(f"\n4. OVERNIGHT SHIFTS: {len(results['overnight_shifts'])} records")
            print(results['overnight_shifts'])
        
        # Summary statistics
        print(f"\n" + "="*60)
        print("SUMMARY STATISTICS")
        print("="*60)
        total_punch_ins = len(self.punch_in_df)
        total_punch_outs = len(self.punch_out_df)
        
        print(f"Total Punch Ins: {total_punch_ins}")
        print(f"Total Punch Outs: {total_punch_outs}")
        print(f"Punch In Only: {len(results['punch_in_only'])}")
        print(f"Punch Out Only: {len(results['punch_out_only'])}")
        print(f"Complete Punches: {len(results['complete_punches'])}")
        
        if 'overnight_shifts' in results:
            print(f"Overnight Shifts: {len(results['overnight_shifts'])}")
    
    def export_results(self, results, output_file='punch_analysis_results.xlsx'):
        """Export results to Excel file"""
        
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            results['punch_in_only'].to_excel(writer, sheet_name='Punch_In_Only', index=False)
            results['punch_out_only'].to_excel(writer, sheet_name='Punch_Out_Only', index=False)
            results['complete_punches'].to_excel(writer, sheet_name='Complete_Punches', index=False)
            
            if 'overnight_shifts' in results:
                results['overnight_shifts'].to_excel(writer, sheet_name='Overnight_Shifts', index=False)
        
        print(f"\nResults exported to {output_file}")
    
    def run_analysis(self):
        """Run complete analysis"""
        
        print("Starting Punch Data Analysis...")
        
        # Load data
        if not self.load_data():
            return
        
        # Clean and prepare data
        self.clean_and_prepare_data()
        
        # Merge data with overnight handling
        self.merge_punch_data()
        
        # Analyze patterns
        results = self.analyze_punch_patterns()
        
        # Generate report
        self.generate_report(results)
        
        # Export results
        self.export_results(results)
        
        return results

# Usage Example
def main():
    """
    Main function to run the analysis
    
    MODIFY THESE FILE PATHS TO MATCH YOUR FILES:
    """
    
    # *** CHANGE THESE PATHS TO YOUR ACTUAL FILE PATHS ***
    punch_in_file = 'punch_in_data.xlsx'      # Your punch in Excel file
    punch_out_file = 'punch_out_data.xlsx'    # Your punch out Excel file
    
    # Create analyzer instance
    analyzer = PunchDataAnalyzer(punch_in_file, punch_out_file)
    
    # Run analysis
    results = analyzer.run_analysis()
    
    return results

if __name__ == "__main__":
    # Run the analysis
    results = main()