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
        
        # If first column contains large values (likely unix timestamps)
        if first_col.max() > 1000000000:
            # Find non-zero values
            non_zero_mask = first_col != 0
            
            # Check if non-zero values are large (unix timestamps) or small (delta)
            non_zero_values = first_col[non_zero_mask].values
            
            if len(non_zero_values) > 0 and non_zero_values[0] > 1000000000:  # Likely unix timestamp (seconds since 1970)
                # Get start and end times from the first and last non-zero values
                start_time = non_zero_values[0]
                end_time = non_zero_values[-1]

                # Rename first column
                df.rename(columns={'col0': 'timestamp'}, inplace=True)

                # Convert to datetime
                df = full_timestamp_expansion(df, start_time, end_time, column='datetime')

                # Drop the original timestamp column
                df.drop(['timestamp'], axis=1, inplace=True)
                
                return df
        
        # If max value of first column is relatively small (<= 10000), likely delta format
        elif first_col.max() <= 10000:
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
            df.rename(columns={'col0': 'delta'}, inplace=True)
            df = delta_timestamp_expansion(df, start_time, delta="delta", column='datetime')
            
            # Rename and drop temporary columns
            df.drop(['delta'], axis=1, inplace=True)
            
            return df
        
        else:
            raise ValueError(f"File {file_path} does not match expected formats.")
        
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


def delta_timestamp_expansion(
    df: pd.DataFrame, start_time: int, delta: str = "Delta", column: str = "Time"
) -> pd.DataFrame:
    """Expands differential timestamps into absolute timestamps in a DataFrame.

    This function takes a DataFrame containing differential timestamps (time differences
    between consecutive events) and converts them into absolute timestamps representing
    specific points in time.

    Args:

    - df: The pandas DataFrame containing the differential timestamps.
    - start_time: The starting timestamp (in seconds) for the first event.
    - delta: The name of the column containing the differential timestamps (default is 'Delta').
    - column: The name of the column where the absolute timestamps will be stored (default is 'Time').

    Returns:

    A pandas DataFrame with a new column containing the absolute timestamps. The original
    DataFrame is truncated to only include rows up to the last non-zero differential
    timestamp entry.

    Raises:

    KeyError: If the specified column 'Delta' is not found in the DataFrame.

    Example:

      >>> import pandas as pd
      >>> data = {'Delta': [0, 0, 5, 3, 0, 7]}
      >>> df = pd.DataFrame(data)
      >>> expanded_df = delta_timestamp_expansion(df, 1600000000)
    """

    # The total time the epoch lasted can then be divided by the length of the array
    time_accumu = df[delta].sum()
    time_sample = np.linspace(0, time_accumu, df.shape[0])

    df[column] = pd.to_datetime(start_time * 1000 + time_sample, unit="ms")

    return df


def full_timestamp_expansion(
    df: pd.DataFrame, start_time: int, end_time: int, column: str = "Time"
) -> pd.DataFrame:
    """Expands timestamps into absolute timestamps in a DataFrame.

    This function takes a DataFrame containing timestamps and converts them into absolute timestamps 
    representing specific points in time.

    Args:

    - df: The pandas DataFrame containing the timestamps.
    - start_time: The starting timestamp (in seconds) for the first event.
    - end_time: The ending timestamp (in seconds) for the last event.
    - column: The name of the column where the absolute timestamps will be stored (default is 'Time').

    Returns:

    A pandas DataFrame with a new column containing the absolute timestamps.

    Example:

      >>> import pandas as pd
      >>> data = {'Timestamp': [0, 0, 1600000000, 16000000010, 0, 1600000030]}
      >>> df = pd.DataFrame(data)
      >>> expanded_df = full_timestamp_expansion(df)
    """

    # The total time the epoch lasted can then be divided by the length of the array
    times = np.linspace(start_time, end_time, df.shape[0])

    df[column] = pd.to_datetime(times, unit="ms")

    return df