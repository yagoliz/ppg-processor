import os
import pandas as pd
from PyQt6.QtCore import QThread, pyqtSignal

from ppg_processor.processing.directory_worker import DirectoryProcessingWorker


class BatchWorker(QThread):
    """
    Worker thread for processing a directory containing participant folders.
    Each participant folder contains multiple session subfolders,
    and each session subfolder should contain a ppg.csv file.

    This allows for a structure like:
    - Main Directory/
        - Participant001/
            - Epoch1/
                - ppg.csv
            - Epoch2/
                - ppg.csv
                - info.txt
        - Participant002/
            - Epoch1/
                - ppg.csv
            ...
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

        # Initialize flags to track processing state
        self.is_running = False
        self.should_stop = False

    def run(self):
        """Process all participant folders and their sessions"""
        try:
            self.is_running = True
            self.should_stop = False

            # Find all participant folders in the directory
            participant_folders = [f.path for f in os.scandir(self.directory_path) if f.is_dir()]

            if not participant_folders:
                self.error.emit(f"No participant folders found in {self.directory_path}")
                return

            self.status.emit(f"Found {len(participant_folders)} participant folders to process")

            # Initialize results dictionary
            results = {}
            for channel in self.channels:
                results[channel] = {
                    "ppi_data": pd.DataFrame(),
                    "hrv_metrics": pd.DataFrame() if self.calculate_hrv else None,
                }

            # Process each participant folder
            for i, participant_folder in enumerate(participant_folders):
                if self.should_stop:
                    self.status.emit("Processing stopped by user")
                    break

                participant_id = os.path.basename(participant_folder)
                self.status.emit(f"Processing participant: {participant_id} ({i + 1}/{len(participant_folders)})")

                # Update overall progress
                overall_progress = int((i / len(participant_folders)) * 100)
                self.progress.emit(overall_progress)

                # Process this participant's sessions using the DirectoryProcessingWorker
                # but we'll collect the results ourselves rather than emitting them
                participant_results = self._process_participant(participant_folder, participant_id)

                if participant_results:
                    # Merge the participant's results into our overall results
                    for channel in self.channels:
                        if channel in participant_results:
                            # Merge PPI data
                            results[channel]["ppi_data"] = pd.concat(
                                [results[channel]["ppi_data"], participant_results[channel]["ppi_data"]]
                            ).sort_values(by="Time")

                            # Merge HRV metrics if available
                            if self.calculate_hrv and "hrv_metrics" in participant_results[channel]:
                                results[channel]["hrv_metrics"] = pd.concat(
                                    [results[channel]["hrv_metrics"], participant_results[channel]["hrv_metrics"]]
                                )

            # Calculate overall HRV metrics across all participants
            if self.calculate_hrv:
                for channel in self.channels:
                    if (
                        "ppi_data" in results[channel]
                        and not results[channel]["ppi_data"].empty
                        and "hrv_metrics" in results[channel]
                        and not results[channel]["hrv_metrics"].empty
                    ):
                        try:
                            self.status.emit(f"Calculating overall HRV metrics for {channel}...")

                            # Calculate overall metrics
                            results[channel]["overall_metrics"] = results[channel]["hrv_metrics"].mean()

                            # Add time range info to overall metrics if used
                            if self.use_time_range:
                                results[channel]["overall_metrics"]["Time_Range"] = f"{self.start_time}-{self.end_time}"

                        except Exception as e:
                            self.status.emit(f"Error calculating overall HRV metrics for {channel}: {str(e)}")

            self.is_running = False
            self.finished_with_result.emit(results)

        except Exception as e:
            self.is_running = False
            self.error.emit(f"Processing error: {str(e)}")

    def _process_participant(self, participant_folder, participant_id):
        """Process a single participant folder with all its session subfolders"""
        try:
            # Find all session folders for this participant
            session_folders = [f.path for f in os.scandir(participant_folder) if f.is_dir()]

            if not session_folders:
                self.status.emit(f"No session folders found for participant {participant_id}")
                return None

            self.status.emit(f"Found {len(session_folders)} sessions for participant {participant_id}")

            # Initialize results for this participant
            participant_results = {}
            for channel in self.channels:
                participant_results[channel] = {
                    "ppi_data": pd.DataFrame(),
                    "hrv_metrics": pd.DataFrame() if self.calculate_hrv else None,
                }

            # Create a directory worker to process all sessions
            # but adapt it to work within our participant processing flow
            worker = DirectoryProcessingWorker(
                directory_path=participant_folder,
                window_size=self.window_size,
                channels=self.channels,
                calculate_hrv=self.calculate_hrv,
                ppi_low_threshold=self.ppi_low_threshold,
                ppi_high_threshold=self.ppi_high_threshold,
                use_time_range=self.use_time_range,
                start_time=self.start_time,
                end_time=self.end_time,
            )

            # Connect to its signals to relay information
            worker.status.connect(self.status.emit)
            worker.error.connect(self.status.emit)  # Only log errors, don't stop overall processing

            # Override progress signal to be a portion of our overall progress
            # We don't connect it directly to avoid having the sub-worker update our main progress

            # Process all sessions for this participant
            worker.run()  # Run synchronously rather than starting a new thread

            # Get results from the worker (this would normally be emitted, but we access it directly)
            session_results = worker._get_results()

            if session_results:
                # Add participant ID to all PPI and HRV data
                for channel in self.channels:
                    if channel in session_results:
                        # Add participant ID to PPI data
                        if "ppi_data" in session_results[channel] and not session_results[channel]["ppi_data"].empty:
                            session_results[channel]["ppi_data"]["Participant"] = participant_id

                        # Add participant ID to HRV metrics
                        if (
                            "hrv_metrics" in session_results[channel]
                            and not session_results[channel]["hrv_metrics"].empty
                        ):
                            session_results[channel]["hrv_metrics"]["Participant"] = participant_id

                return session_results

            return None

        except Exception as e:
            self.status.emit(f"Error processing participant {participant_id}: {str(e)}")
            return None

    def stop(self):
        """Signal the worker to stop processing"""
        self.should_stop = True
