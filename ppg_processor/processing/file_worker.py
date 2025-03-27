"""
Worker class for processing a single PPG file
"""

import pandas as pd
import neurokit2 as nk
from PyQt6.QtCore import QThread, pyqtSignal

from processing.filters import bandpass_filter
from processing.hrv_metrics import calculate_hrv_metrics
from ppg_processor.utils.io_utils import read_ppg_file

class PPGProcessingWorker(QThread):
    """
    Worker thread for processing a single PPG file
    """
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    error = pyqtSignal(str)
    finished_with_result = pyqtSignal(dict)
    
    def __init__(self, file_path, window_size=5, channels=None, calculate_hrv=True, 
                 ppi_low_threshold=667, ppi_high_threshold=2000):
        super().__init__()
        self.file_path = file_path
        self.window_size = window_size
        self.channels = channels or ["P0", "P1", "P2"]
        self.calculate_hrv = calculate_hrv
        self.ppi_low_threshold = ppi_low_threshold
        self.ppi_high_threshold = ppi_high_threshold
        
    def run(self):
        try:          
            self.status.emit(f"Reading PPG file: {self.file_path}")
            try:
                ppg = read_ppg_file(self.file_path)
            except ValueError as e:
                self.error.emit(str(e))
                return
            
            # Set datetime as index if it's not already
            if 'datetime' in ppg.columns:
                ppg.set_index('datetime', inplace=True)
            
            if ppg.empty:
                self.error.emit("No data found in the file.")
                return
                
            # Calculate sampling rate
            self.status.emit("Calculating sampling rate...")
            if isinstance(ppg.index, pd.DatetimeIndex):
                time_diffs = ppg.index.to_series().diff().dt.total_seconds()
            else:
                self.error.emit("Index is not a datetime index. Cannot calculate sampling rate.")
                return
                
            time_diffs = time_diffs[time_diffs < 10.0]  # Remove outliers
            if time_diffs.empty:
                self.error.emit("Unable to calculate sampling rate from timestamps.")
                return
                
            avg_sampling_rate = 1 / time_diffs.mean()
            self.status.emit(f"Average sampling rate: {avg_sampling_rate:.2f} Hz")

            # Preprocess the PPG data (apply bandpass filter)
            self.status.emit("Preprocessing PPG signals...")
            try:
                # Check if AMBIENT column exists
                has_ambient = "AMBIENT" in ppg.columns
                
                # Process each channel
                for channel in self.channels:
                    if channel not in ppg.columns:
                        self.error.emit(f"Channel {channel} not found in data.")
                        continue
                        
                    # Remove ambient if available and apply filter
                    if has_ambient:
                        ppg[channel] = bandpass_filter(
                            (ppg[channel] - ppg["AMBIENT"]).to_numpy(), 
                            0.5, 4.0, avg_sampling_rate, 11
                        )
                    else:
                        ppg[channel] = bandpass_filter(
                            ppg[channel].to_numpy(), 
                            0.5, 4.0, avg_sampling_rate, 11
                        )
            except Exception as e:
                self.error.emit(f"Error preprocessing PPG: {str(e)}")
                return

            # Main processing loop - calculate PPI for each channel
            self.status.emit("Calculating PPI values...")
            results = {}
            
            for i, channel in enumerate(self.channels):
                if channel not in ppg.columns:
                    continue
                    
                hrv_results = pd.DataFrame()
                total_windows = len(list(ppg.groupby(pd.Grouper(freq=f"{self.window_size}min"))))
                
                for j, sample in enumerate(ppg.groupby(pd.Grouper(freq=f"{self.window_size}min"))):
                    try:
                        current_time = sample[0]
                        data = sample[1]
                        
                        if data.empty:
                            continue
                        
                        # Update progress
                        progress_pct = int((j / total_windows) * 100 / len(self.channels) + (i * 100 / len(self.channels)))
                        self.progress.emit(progress_pct)
                        
                        # Process PPG data
                        hrv_sample, info = nk.ppg_process(
                            data[channel].to_numpy(), 
                            sampling_rate=int(avg_sampling_rate)
                        )
                        
                        # Extract peaks and create dataframe
                        data_sample = data[[channel]].copy().reset_index()
                        data_sample["PPG_Peaks"] = hrv_sample["PPG_Peaks"]
                        data_sample["Quality"] = hrv_sample["PPG_Quality"]
                        data_sample = data_sample[data_sample["PPG_Peaks"] == 1]
                        
                        # Concatenate results
                        hrv_results = pd.concat([hrv_results, data_sample], ignore_index=True)
                        
                    except Exception as e:
                        self.status.emit(f"Error processing window at {current_time}: {str(e)}")
                        continue
                
                # Calculate PPI values
                if not hrv_results.empty:
                    # Rename datetime column to Time for consistency with provided functions
                    if isinstance(hrv_results.index, pd.DatetimeIndex):
                        # Convert index to column
                        hrv_results = hrv_results.reset_index()
                        hrv_results.rename(columns={'index': 'Time'}, inplace=True)
                    elif 'datetime' in hrv_results.columns:
                        hrv_results.rename(columns={'datetime': 'Time'}, inplace=True)
                    elif 'timestamp' in hrv_results.columns:
                        hrv_results.rename(columns={'timestamp': 'Time'}, inplace=True)
                    
                    # Sort by time
                    hrv_results = hrv_results.sort_values(by='Time')
                    
                    # Calculate PPI values
                    hrv_results['PPI'] = hrv_results['Time'].diff().dt.total_seconds() * 1000  # ms
                
                # Clean PPI data - remove outliers
                self.status.emit(f"Cleaning PPI data for channel {channel}...")
                cleaned_results = hrv_results.copy()
                if 'PPI' in cleaned_results.columns:
                    # Remove first row (NaN PPI) and rows outside threshold
                    cleaned_results = cleaned_results.dropna(subset=['PPI'])
                    initial_len = len(cleaned_results)
                    cleaned_results = cleaned_results[
                        (cleaned_results['PPI'] >= self.ppi_low_threshold) & 
                        (cleaned_results['PPI'] <= self.ppi_high_threshold)
                    ]
                    removed = initial_len - len(cleaned_results)
                    self.status.emit(f"Removed {removed} outlier PPI values from channel {channel}")
                
                # Calculate HRV metrics if requested
                hrv_metrics = None
                if self.calculate_hrv and 'PPI' in cleaned_results.columns and not cleaned_results.empty:
                    self.status.emit(f"Calculating HRV metrics for channel {channel}...")
                    try:
                        # Use the provided functions to calculate HRV metrics
                        hrv_metrics = calculate_hrv_metrics(
                            cleaned_results[['Time', 'PPI', 'Quality']], 
                            window=self.window_size
                        )
                        self.status.emit(f"Calculated HRV metrics for {len(hrv_metrics)} windows")
                    except Exception as e:
                        self.status.emit(f"Error calculating HRV metrics: {str(e)}")
                
                # Store both PPI and HRV data
                results[channel] = {
                    'ppi_data': cleaned_results,
                    'hrv_metrics': hrv_metrics
                }
                
            self.finished_with_result.emit(results)
            
        except Exception as e:
            self.error.emit(f"Processing error: {str(e)}")