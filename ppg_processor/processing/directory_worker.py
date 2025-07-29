"""
Worker class for processing a directory of PPG files
"""

import datetime
import os
import pandas as pd
import neurokit2 as nk
from PyQt6.QtCore import QThread, pyqtSignal

from ppg_processor.processing.filters import bandpass_filter
from ppg_processor.processing.hrv_metrics import calculate_hrv_metrics
from ppg_processor.utils.io_utils import read_ppg_file


class DirectoryProcessingWorker(QThread):
    """
    Worker thread for processing a directory containing PPG files
    Each subfolder should contain a ppg.csv file
    """

    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    error = pyqtSignal(str)
    finished_with_result = pyqtSignal(dict)

    def __init__(
        self,
        directory_path,
        window_size=5,
        channels=None,
        calculate_hrv=True,
        ppi_low_threshold=667,
        ppi_high_threshold=2000,
        use_time_range=False,
        start_time=None,
        end_time=None,
    ):
        super().__init__()
        self.directory_path = directory_path
        self.window_size = window_size
        self.channels = channels or ["P0", "P1", "P2"]
        self.calculate_hrv = calculate_hrv
        self.ppi_low_threshold = ppi_low_threshold
        self.ppi_high_threshold = ppi_high_threshold
        self.use_time_range = use_time_range
        self.start_time = start_time
        self.end_time = end_time

    def run(self):
        try:
            self.should_stop = False

            self._results = self._process_directory()

            if self._results:
                self.finished_with_result.emit(self._results)

        except Exception as e:
            self.error.emit(f"Directory Worker Error: {str(e)}")

    def _get_results(self):
        """Returns the results of the processing - Can be called after run() completes"""
        return self._results

    def _process_directory(self):
        """Process all PPG files in the participant directory"""

        # Find all folders in the directory with numeric names
        subfolders = [f.path for f in os.scandir(self.directory_path) if f.is_dir() and f.name.isdigit()]

        if not subfolders:
            self.error.emit(f"No subfolders found in {self.directory_path}")
            return

        self.status.emit(f"Found {len(subfolders)} folders to process")

        # Initialize results dictionary
        results = {}
        for channel in self.channels:
            results[channel] = {
                "ppi_data": pd.DataFrame(),
                "hrv_metrics": pd.DataFrame() if self.calculate_hrv else None,
            }

        # Process each folder
        subfolders.sort()  # Sort folders for consistent processing
        for i, folder in enumerate(subfolders):
            # Update progress
            progress_pct = int((i / len(subfolders)) * 100)
            self.progress.emit(progress_pct)

            # Inside the folder loop:
            ppg_file = os.path.join(folder, "ppg.csv")

            if not os.path.exists(ppg_file):
                self.status.emit(f"No ppg.csv found in {folder}, skipping")
                continue

            self.status.emit(f"Processing {ppg_file}")

            try:
                # Read with folder path for info.txt lookup
                ppg = read_ppg_file(ppg_file, folder_path=folder)

                # Set datetime as index if it's not already
                if "datetime" in ppg.columns and not isinstance(ppg.index, pd.DatetimeIndex):
                    ppg.set_index("datetime", inplace=True)
                
                # Assert that the index is a datetime index
                if not isinstance(ppg.index, pd.DatetimeIndex):
                    self.error.emit("PPG data must have a datetime index.")
                    return

                # If time range is enabled, filter the data
                if self.use_time_range and self.start_time and self.end_time:
                    # Convert string times to datetime.time objects
                    start_time = datetime.datetime.strptime(self.start_time, "%H:%M")
                    end_time = datetime.datetime.strptime(self.end_time, "%H:%M")

                    # Here we need to a trick because we assume that the days start at 12:00 PM so that we can get night time HRV
                    delta_time = datetime.timedelta(hours=12)
                    start_time = (start_time + delta_time).time()
                    end_time = (end_time + delta_time).time()

                    if start_time > end_time:
                        self.error.emit("Start time must be before end time. Note that times are adjusted by 12 hours to allow night time HRV.")
                        return

                    # Filter based on time of day
                    ppg.index = ppg.index + delta_time  # Adjust index to match the time range
                    ppg = ppg[
                        (ppg.index.time >= start_time) & (ppg.index.time <= end_time)
                    ]

                    # If PPG is empty after filtering, emit status
                    if ppg.empty:
                        self.status.emit(f"No data points in selected time range: {self.start_time}-{self.end_time}")
                        continue

                # Calculate sampling rate
                if isinstance(ppg.index, pd.DatetimeIndex):
                    time_diffs = ppg.index.to_series().diff().dt.total_seconds()
                    time_diffs = time_diffs[time_diffs < 10.0]  # Remove outliers
                    if time_diffs.empty:
                        self.status.emit(f"Unable to calculate sampling rate for {folder}, skipping")
                        continue
                    avg_sampling_rate = 1 / time_diffs.mean()
                else:
                    self.status.emit(f"No timestamp column found in {folder}, skipping")
                    continue

                # Process each channel
                for channel in self.channels:
                    if channel not in ppg.columns:
                        self.status.emit(f"Channel {channel} not found in {folder}")
                        continue

                    # Apply bandpass filter
                    has_ambient = "AMBIENT" in ppg.columns
                    if has_ambient:
                        ppg[channel] = bandpass_filter(
                            (ppg[channel] - ppg["AMBIENT"]).to_numpy(),
                            0.5,
                            4.0,
                            avg_sampling_rate,
                            11,
                        )
                    else:
                        ppg[channel] = bandpass_filter(ppg[channel].to_numpy(), 0.5, 4.0, avg_sampling_rate, 11)

                    # Process PPG data for this channel
                    hrv_sample, info = nk.ppg_process(
                        ppg[channel].to_numpy(),
                        sampling_rate=int(avg_sampling_rate),
                    )

                    # Extract peaks
                    data_sample = ppg[[channel]].copy().reset_index()
                    data_sample["PPG_Peaks"] = hrv_sample["PPG_Peaks"]
                    data_sample["Quality"] = hrv_sample["PPG_Quality"]
                    data_sample = data_sample[data_sample["PPG_Peaks"] == 1]

                    # Rename datetime column to Time for consistency
                    if "index" in data_sample.columns:
                        data_sample.rename(columns={"index": "Time"}, inplace=True)
                    elif "datetime" in data_sample.columns:
                        data_sample.rename(columns={"datetime": "Time"}, inplace=True)
                    elif "timestamp" in data_sample.columns:
                        data_sample.rename(columns={"timestamp": "Time"}, inplace=True)

                    # Sort by time
                    data_sample = data_sample.sort_values(by="Time")
                    
                    # Revert the delta time adjustment
                    if self.use_time_range:
                        data_sample["Time"] = data_sample["Time"] - delta_time

                    # Calculate PPI values
                    data_sample["PPI"] = data_sample["Time"].diff().dt.total_seconds() * 1000  # ms

                    # Clean PPI data - remove outliers
                    if "PPI" in data_sample.columns:
                        # Remove first row (NaN PPI) and rows outside threshold
                        data_sample = data_sample.dropna(subset=["PPI"])
                        initial_len = len(data_sample)
                        data_sample = data_sample[
                            (data_sample["PPI"] >= self.ppi_low_threshold)
                            & (data_sample["PPI"] <= self.ppi_high_threshold)
                        ]
                        removed = initial_len - len(data_sample)
                        self.status.emit(f"Removed {removed} outlier PPI values from {folder}")

                    # Add folder name as identifier
                    data_sample["Folder"] = os.path.basename(folder)

                    # Append to results
                    results[channel]["ppi_data"] = pd.concat([results[channel]["ppi_data"], data_sample]).sort_values(
                        by="Time"
                    )

            except Exception as e:
                self.status.emit(f"Error processing {folder}: {str(e)}")

        # Fill progress bar
        self.progress.emit(100)

        # Calculate HRV metrics on combined data
        if self.calculate_hrv:
            for channel in self.channels:
                if "ppi_data" in results[channel] and not results[channel]["ppi_data"].empty:
                    try:
                        self.status.emit(f"Calculating HRV metrics for {channel} on combined data...")

                        # Use the provided functions to calculate HRV metrics
                        results[channel]["hrv_metrics"] = calculate_hrv_metrics(
                            results[channel]["ppi_data"][["Time", "PPI", "Quality"]],
                            window=self.window_size,
                        )

                        # Calculate overall metrics
                        results[channel]["overall_metrics"] = results[channel]["hrv_metrics"].mean()

                        # Add folder information if possible
                        if "Folder" in results[channel]["ppi_data"].columns:
                            # For each window, find closest ppi data point and get its folder
                            for idx, row in results[channel]["hrv_metrics"].iterrows():
                                start_time = row["Start_Time"]
                                closest_idx = abs(results[channel]["ppi_data"]["Time"] - start_time).idxmin()
                                results[channel]["hrv_metrics"].at[idx, "Folder"] = results[channel]["ppi_data"].at[
                                    closest_idx, "Folder"
                                ]

                        self.status.emit(f"Calculated HRV metrics for {len(results[channel]['hrv_metrics'])} windows")
                    except Exception as e:
                        self.status.emit(f"Error calculating HRV metrics for {channel}: {str(e)}")

        return results

    def stop(self):
        """Stop the processing thread"""
        self.should_stop = True
