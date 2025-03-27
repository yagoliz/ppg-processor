import re
import os
import pandas as pd
import numpy as np

def read_ppg_file(file_path: str, folder_path: str = None) -> pd.DataFrame:
    """
    Read PPG data from CSV file without headers, handling different formats:
    1. Format with timestamp column with batched rows (zeros)
    2. Format with delta column + info.txt file with start_time
    
    Args:
        file_path (str): Path to the PPG file
        folder_path (str, optional): Path to the folder containing the file (for info.txt)
        
    Returns:
        pd.DataFrame: DataFrame with standardized columns
    """
    try:
        # Read CSV without headers
        df = pd.read_csv(file_path, header=None)
        
        # Assign default column names
        if len(df.columns) >= 5:
            df.columns = ['col0', 'P0', 'P1', 'P2', 'AMBIENT'] + [f'extra{i}' for i in range(len(df.columns)-5)]
        else:
            raise ValueError(f"File has unexpected number of columns: {len(df.columns)}")
        
        # Check the first column to determine format
        first_col = df['col0']
        
        # If first column contains zeros, likely timestamp format with batches
        if first_col.eq(0).any():
            # Find non-zero values
            non_zero_mask = first_col != 0
            
            # Check if non-zero values are large (unix timestamps) or small (delta)
            non_zero_values = first_col[non_zero_mask].values
            
            if len(non_zero_values) > 0 and non_zero_values[0] > 1000000000:  # Likely unix timestamp (seconds since 1970)
                # Process as timestamp format
                timestamp_indices = df.index[non_zero_mask].tolist()
                
                # Add the final index for last batch calculation
                timestamp_indices.append(len(df))
                
                # Create datetime column
                df['datetime'] = pd.NaT
                
                # Process each batch
                for i in range(len(timestamp_indices) - 1):
                    start_idx = timestamp_indices[i]
                    end_idx = timestamp_indices[i+1]
                    
                    # Get batch timestamp (in seconds)
                    batch_timestamp = df.loc[start_idx, 'col0']
                    
                    # Estimate sampling rate (assuming 50Hz if we can't determine)
                    sample_rate = 0.02  # 20ms (50Hz)
                    
                    # Set datetime for each row in batch
                    for j, idx in enumerate(range(start_idx, end_idx)):
                        df.loc[idx, 'datetime'] = pd.to_datetime(batch_timestamp + j * sample_rate, unit='s')
                
                # Rename first column
                df.rename(columns={'col0': 'timestamp'}, inplace=True)
                
                return df
        
        # If max value of first column is relatively small (<= 10000), likely delta format
        if first_col.max() <= 10000:
            # Process as delta format
            info_file = os.path.join(folder_path or os.path.dirname(file_path), 'info.txt')
            start_time = None
            
            # Read info.txt to get start_time
            if os.path.exists(info_file):
                with open(info_file, 'r') as f:
                    info_content = f.read()
                    match = re.search(r'start_time:\s*(\d+)', info_content)
                    if match:
                        start_time = int(match.group(1))
            
            if start_time is None:
                raise ValueError(f"Cannot find start_time in info.txt file for {file_path}")
            
            # Calculate cumulative deltas (in milliseconds)
            df['datetime'] = pd.to_datetime(start_time, unit='s')
            df['cumulative_delta'] = df['col0'].cumsum()
            
            # Apply delta times
            for i in range(len(df)):
                if i > 0:  # Skip first row (already has correct start_time)
                    df.loc[i, 'datetime'] = df.loc[0, 'datetime'] + pd.Timedelta(milliseconds=df.loc[i, 'cumulative_delta'])
            
            # Rename and drop temporary columns
            df.rename(columns={'col0': 'delta'}, inplace=True)
            df.drop(['delta', 'cumulative_delta'], axis=1, inplace=True)
            
            return df
        
        # If first column has uniform incrementing values, might be a standard format with row indices
        if is_incrementing_sequence(first_col.values):
            # Try to see if second column is timestamp
            if 'col1' in df.columns and df['col1'].max() > 1000000000:
                # Second column might be timestamp
                df['datetime'] = pd.to_datetime(df['col1'], unit='s')
                # Adjust column names
                new_columns = ['index', 'timestamp', 'P0', 'P1', 'P2', 'AMBIENT']
                if len(df.columns) > 6:
                    new_columns += [f'extra{i}' for i in range(len(df.columns)-6)]
                df.columns = new_columns[:len(df.columns)]
                
                return df
            else:
                # No clear timestamp, try to infer a simple incrementing index
                if folder_path is not None:
                    info_file = os.path.join(folder_path, 'info.txt')
                    if os.path.exists(info_file):
                        with open(info_file, 'r') as f:
                            info_content = f.read()
                            match = re.search(r'start_time:\s*(\d+)', info_content)
                            if match:
                                start_time = int(match.group(1))
                                
                                # Create evenly spaced timestamps
                                df['datetime'] = pd.date_range(
                                    start=pd.to_datetime(start_time, unit='s'),
                                    periods=len(df),
                                    freq='20ms'  # Assume 50Hz sampling rate
                                )
                                return df
        
        # Last resort: try to use the file's modification time as a base
        # and create evenly spaced timestamps assuming 50Hz sampling
        file_mtime = os.path.getmtime(file_path)
        start_time = file_mtime - (len(df) / 50)  # Subtract total recording time
        
        df['datetime'] = pd.date_range(
            start=pd.to_datetime(start_time, unit='s'),
            periods=len(df),
            freq='20ms'  # Assume 50Hz sampling rate
        )
        
        # Rename columns to standard names
        df.rename(columns={'col0': 'original_col0'}, inplace=True)
        
        return df
        
    except Exception as e:
        raise ValueError(f"Error reading file {file_path}: {str(e)}")

def is_incrementing_sequence(arr: np.ndarray, tolerance: float = 0.1) -> bool:
    """Check if an array is approximately an incrementing sequence"""
    if len(arr) < 2:
        return True
        
    diffs = np.diff(arr)
    mean_diff = np.mean(diffs)
    
    # Check if most differences are within tolerance of the mean difference
    return np.sum(np.abs(diffs - mean_diff) < tolerance * mean_diff) / len(diffs) > 0.9