"""
Main application window for the PPG Processor
"""

import os
import pandas as pd
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QFileDialog,
    QComboBox,
    QCheckBox,
    QSpinBox,
    QGroupBox,
    QProgressBar,
    QTabWidget,
    QMessageBox,
    QStatusBar,
    QGridLayout,
    QRadioButton,
    QTimeEdit,
)
from PyQt6.QtCore import QTime

import pyqtgraph as pg

from ppg_processor.processing.file_worker import PPGProcessingWorker
from ppg_processor.processing.directory_worker import DirectoryProcessingWorker
from ppg_processor.processing.batch_worker import BatchWorker


class PPGProcessorApp(QMainWindow):
    """Main application window for the PPG Processor"""

    def __init__(self):
        super().__init__()

        self.setWindowTitle("PPG to PPI Processor")
        self.setGeometry(100, 100, 1000, 1000)

        # Set window icon
        icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "icon.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.init_ui()

        # Store processing results
        self.results = {}
        self.current_file = None
        self.current_directory = None

    def init_ui(self):
        """Initialize the user interface"""
        # Main widget and layout
        main_widget = QWidget()
        main_layout = QVBoxLayout()

        # File selection area
        file_group = self.init_file_selection_ui()

        # Settings area
        settings_group = self.init_settings_ui()

        # Processing buttons
        process_layout = QHBoxLayout()
        self.process_btn = QPushButton("Process")
        self.process_btn.clicked.connect(self.process_file)
        self.process_btn.setEnabled(False)

        self.save_btn = QPushButton("Save Results")
        self.save_btn.clicked.connect(self.save_results)
        self.save_btn.setEnabled(False)

        process_layout.addWidget(self.process_btn)
        process_layout.addWidget(self.save_btn)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)

        # Results tabs
        self.results_tabs = QTabWidget()

        # Add components to main layout
        main_layout.addWidget(file_group)
        main_layout.addWidget(settings_group)
        main_layout.addLayout(process_layout)
        main_layout.addWidget(self.progress_bar)
        main_layout.addWidget(self.results_tabs, 1)  # Give it stretch factor

        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")

        # Set layout
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)

    def init_file_selection_ui(self):
        """Initialize the file selection part of the UI"""
        # File selection area
        file_group = QGroupBox("Data Input")
        file_layout = QVBoxLayout()

        # Create radio buttons for input type selection
        input_type_layout = QHBoxLayout()
        self.file_radio = QRadioButton("Single CSV File")
        self.file_radio.setChecked(True)
        self.file_radio.toggled.connect(self.toggle_input_type)

        self.directory_radio = QRadioButton("Directory with PPG Files")
        self.directory_radio.toggled.connect(self.toggle_input_type)

        self.participant_radio = QRadioButton("Participant Directories")
        self.participant_radio.toggled.connect(self.toggle_input_type)
        self.participant_radio.setToolTip(
            "Process a directory of participant folders, each containing multiple epoch folders with PPG data"
        )

        input_type_layout.addWidget(self.file_radio)
        input_type_layout.addWidget(self.directory_radio)
        input_type_layout.addWidget(self.participant_radio)
        file_layout.addLayout(input_type_layout)

        # Single file selection
        file_path_layout = QHBoxLayout()
        file_path_layout.addWidget(QLabel("File:"))
        self.file_path_label = QLabel("No file selected")
        self.browse_file_btn = QPushButton("Browse...")
        self.browse_file_btn.clicked.connect(self.browse_file)

        file_path_layout.addWidget(self.file_path_label, 1)  # Give stretch factor
        file_path_layout.addWidget(self.browse_file_btn)

        # Directory selection
        dir_path_layout = QHBoxLayout()
        dir_path_layout.addWidget(QLabel("Directory:"))
        self.dir_path_label = QLabel("No directory selected")
        self.browse_dir_btn = QPushButton("Browse...")
        self.browse_dir_btn.clicked.connect(self.browse_directory)

        dir_path_layout.addWidget(self.dir_path_label, 1)  # Give stretch factor
        dir_path_layout.addWidget(self.browse_dir_btn)

        # Batch participant processing
        participant_path_layout = QHBoxLayout()
        participant_path_layout.addWidget(QLabel("Participant Directory:"))
        self.participant_path_label = QLabel("No directory selected")
        self.browse_participant_btn = QPushButton("Browse...")
        self.browse_participant_btn.clicked.connect(self.browse_directory)

        participant_path_layout.addWidget(self.participant_path_label, 1)  # Give stretch factor
        participant_path_layout.addWidget(self.browse_participant_btn)

        # Add the three layouts
        self.file_selection_widget = QWidget()
        self.file_selection_widget.setLayout(file_path_layout)

        self.dir_selection_widget = QWidget()
        self.dir_selection_widget.setLayout(dir_path_layout)
        self.dir_selection_widget.setVisible(False)  # Hidden by default

        self.participant_selection_widget = QWidget()
        self.participant_selection_widget.setLayout(participant_path_layout)
        self.participant_selection_widget.setVisible(False)  # Hidden by default

        file_layout.addWidget(self.file_selection_widget)
        file_layout.addWidget(self.dir_selection_widget)
        file_layout.addWidget(self.participant_selection_widget)

        file_group.setLayout(file_layout)
        return file_group

    def init_settings_ui(self):
        """Initialize the settings part of the UI"""
        # Settings area
        settings_group = QGroupBox("Processing Settings")
        settings_layout = QGridLayout()

        # Window size setting
        settings_layout.addWidget(QLabel("Window Size:"), 0, 0)
        self.window_size_spin = QSpinBox()
        self.window_size_spin.setRange(1, 60)
        self.window_size_spin.setValue(5)
        self.window_size_spin.setSuffix(" min")
        settings_layout.addWidget(self.window_size_spin, 0, 1)

        # Channel selection
        settings_layout.addWidget(QLabel("Channels:"), 1, 0)
        self.channel_p0_check = QCheckBox("P0")
        self.channel_p0_check.setChecked(True)
        self.channel_p1_check = QCheckBox("P1")
        self.channel_p1_check.setChecked(True)
        self.channel_p2_check = QCheckBox("P2")
        self.channel_p2_check.setChecked(True)

        channel_layout = QHBoxLayout()
        channel_layout.addWidget(self.channel_p0_check)
        channel_layout.addWidget(self.channel_p1_check)
        channel_layout.addWidget(self.channel_p2_check)
        settings_layout.addLayout(channel_layout, 1, 1)

        # Output format selection
        settings_layout.addWidget(QLabel("Output Format:"), 2, 0)
        self.output_format_combo = QComboBox()
        self.output_format_combo.addItem("CSV")
        settings_layout.addWidget(self.output_format_combo, 2, 1)

        # HRV calculation option
        self.calculate_hrv_check = QCheckBox("Calculate HRV Metrics")
        self.calculate_hrv_check.setChecked(True)
        settings_layout.addWidget(self.calculate_hrv_check, 3, 0, 1, 2)

        # Add time range UI
        time_range_group = self.init_time_range_ui()
        settings_layout.addWidget(time_range_group, 4, 0, 1, 2)

        # PPI threshold settings
        threshold_group = QGroupBox("PPI Thresholds (outlier removal)")
        threshold_layout = QGridLayout()
        threshold_layout.addWidget(QLabel("Min:"), 0, 0)
        self.ppi_low_threshold_spin = QSpinBox()
        self.ppi_low_threshold_spin.setRange(300, 1000)
        self.ppi_low_threshold_spin.setValue(667)
        self.ppi_low_threshold_spin.setSuffix(" ms")
        threshold_layout.addWidget(self.ppi_low_threshold_spin, 0, 1)

        threshold_layout.addWidget(QLabel("Max:"), 1, 0)
        self.ppi_high_threshold_spin = QSpinBox()
        self.ppi_high_threshold_spin.setRange(1000, 3000)
        self.ppi_high_threshold_spin.setValue(2000)
        self.ppi_high_threshold_spin.setSuffix(" ms")
        threshold_layout.addWidget(self.ppi_high_threshold_spin, 1, 1)
        threshold_group.setLayout(threshold_layout)

        settings_layout.addWidget(threshold_group, 5, 0, 1, 2)

        settings_group.setLayout(settings_layout)
        return settings_group

    def toggle_input_type(self):
        """Toggle between file and directory input modes"""
        # Show/hide the appropriate input widgets
        is_file_mode = self.file_radio.isChecked()
        self.file_selection_widget.setVisible(is_file_mode)
        self.dir_selection_widget.setVisible(not is_file_mode)

        # Reset selection
        self.current_file = None
        self.current_directory = None
        self.file_path_label.setText("No file selected")
        self.dir_path_label.setText("No directory selected")
        self.process_btn.setEnabled(False)

    def init_time_range_ui(self):
        """Create the time range selection UI components"""
        time_range_group = QGroupBox("Time Range Filter")
        time_range_layout = QGridLayout()

        # Checkbox to enable/disable time range filtering
        self.use_time_range_check = QCheckBox("Filter by Time Range")
        self.use_time_range_check.toggled.connect(self.toggle_time_range)

        # Time editors for start and end times
        time_range_layout.addWidget(QLabel("Start Time:"), 1, 0)
        self.start_time_edit = QTimeEdit()
        self.start_time_edit.setDisplayFormat("HH:mm")
        self.start_time_edit.setTime(QTime(0, 0))  # Default 00:00
        self.start_time_edit.setEnabled(False)
        time_range_layout.addWidget(self.start_time_edit, 1, 1)

        time_range_layout.addWidget(QLabel("End Time:"), 2, 0)
        self.end_time_edit = QTimeEdit()
        self.end_time_edit.setDisplayFormat("HH:mm")
        self.end_time_edit.setTime(QTime(4, 59))  # Default 04:59
        self.end_time_edit.setEnabled(False)
        time_range_layout.addWidget(self.end_time_edit, 2, 1)

        self.use_time_range_check.setChecked(True)
        time_range_layout.addWidget(self.use_time_range_check, 0, 0, 1, 2)
        time_range_group.setLayout(time_range_layout)

        return time_range_group

    def toggle_time_range(self, checked):
        """Enable or disable time range selection"""
        self.start_time_edit.setEnabled(checked)
        self.end_time_edit.setEnabled(checked)

    def browse_file(self):
        """Browse for a single CSV file"""
        file_path, _ = QFileDialog.getOpenFileName(self, "Select PPG File", "", "CSV Files (*.csv)")

        if file_path:
            self.file_path_label.setText(file_path)
            self.current_file = file_path
            self.current_directory = None
            self.process_btn.setEnabled(True)
            self.status_bar.showMessage(f"File selected: {os.path.basename(file_path)}")

    def browse_directory(self):
        """Browse for a directory containing PPG data folders"""
        dir_path = QFileDialog.getExistingDirectory(self, "Select Directory with PPG Files")

        if dir_path:
            self.dir_path_label.setText(dir_path)
            self.current_directory = dir_path
            self.current_file = None
            self.process_btn.setEnabled(True)
            self.status_bar.showMessage(f"Directory selected: {os.path.basename(dir_path)}")

    def process_file(self):
        """Process the selected file or directory"""
        # Get selected channels
        channels = []
        if self.channel_p0_check.isChecked():
            channels.append("P0")
        if self.channel_p1_check.isChecked():
            channels.append("P1")
        if self.channel_p2_check.isChecked():
            channels.append("P2")

        if not channels:
            QMessageBox.warning(self, "No Channels", "Please select at least one channel to process.")
            return

        # Clear previous results
        self.results = {}
        self.results_tabs.clear()

        # Setup progress tracking
        self.progress_bar.setValue(0)

        # Determine processing mode
        is_file_mode = self.file_radio.isChecked()
        is_dir_mode = self.directory_radio.isChecked()
        is_batch_mode = self.participant_radio.isChecked()

        # Create and start worker thread
        if is_file_mode and self.current_file:
            self.worker = PPGProcessingWorker(
                file_path=self.current_file,
                window_size=self.window_size_spin.value(),
                channels=channels,
                calculate_hrv=self.calculate_hrv_check.isChecked(),
                ppi_low_threshold=self.ppi_low_threshold_spin.value(),
                ppi_high_threshold=self.ppi_high_threshold_spin.value(),
                use_time_range=self.use_time_range_check.isChecked(),
                start_time=self.start_time_edit.time().toString("HH:mm")
                if self.use_time_range_check.isChecked()
                else None,
                end_time=self.end_time_edit.time().toString("HH:mm") if self.use_time_range_check.isChecked() else None,
            )
        elif is_dir_mode and self.current_directory:
            self.worker = DirectoryProcessingWorker(
                directory_path=self.current_directory,
                window_size=self.window_size_spin.value(),
                channels=channels,
                calculate_hrv=self.calculate_hrv_check.isChecked(),
                ppi_low_threshold=self.ppi_low_threshold_spin.value(),
                ppi_high_threshold=self.ppi_high_threshold_spin.value(),
                use_time_range=self.use_time_range_check.isChecked(),
                start_time=self.start_time_edit.time().toString("HH:mm")
                if self.use_time_range_check.isChecked()
                else None,
                end_time=self.end_time_edit.time().toString("HH:mm") if self.use_time_range_check.isChecked() else None,
            )
        elif is_batch_mode and self.current_directory:
            self.worker = BatchWorker(
                directory_path=self.current_directory,
                window_size=self.window_size_spin.value(),
                channels=channels,
                calculate_hrv=self.calculate_hrv_check.isChecked(),
                ppi_low_threshold=self.ppi_low_threshold_spin.value(),
                ppi_high_threshold=self.ppi_high_threshold_spin.value(),
                use_time_range=self.use_time_range_check.isChecked(),
                start_time=self.start_time_edit.time().toString("HH:mm")
                if self.use_time_range_check.isChecked()
                else None,
                end_time=self.end_time_edit.time().toString("HH:mm") if self.use_time_range_check.isChecked() else None,
            )
        else:
            QMessageBox.warning(self, "No Input", "Please select a file or directory to process.")
            return

        self.worker.progress.connect(self.update_progress)
        self.worker.status.connect(self.update_status)
        self.worker.error.connect(self.show_error)
        self.worker.finished_with_result.connect(self.display_results)

        # Disable UI during processing
        self.process_btn.setEnabled(False)
        self.save_btn.setEnabled(False)
        self.browse_file_btn.setEnabled(False)
        self.browse_dir_btn.setEnabled(False)

        # Start processing
        self.worker.start()

    def update_progress(self, value):
        """Update the progress bar"""
        self.progress_bar.setValue(value)

    def update_status(self, message):
        """Update the status bar with a message"""
        self.status_bar.showMessage(message)

    def show_error(self, message):
        """Display an error message"""
        QMessageBox.critical(self, "Error", message)
        self.process_btn.setEnabled(True)
        self.browse_file_btn.setEnabled(True)
        self.browse_dir_btn.setEnabled(True)

    def display_results(self, results):
        """Display the processing results"""
        self.results = results
        
        # Re-enable UI
        self.process_btn.setEnabled(True)
        self.browse_file_btn.setEnabled(True)
        self.browse_dir_btn.setEnabled(True)
        self.browse_participant_btn.setEnabled(True)
        self.save_btn.setEnabled(True)
        
        # Display results in tabs
        self.results_tabs.clear()
        
        for channel, result_dict in results.items():
            ppi_data = result_dict['ppi_data']
            hrv_metrics = result_dict['hrv_metrics']
            overall_metrics = result_dict.get('overall_metrics')
            
            if ppi_data.empty:
                continue
                
            # Create a tab for this channel
            tab = QTabWidget()  # Use tab widget for PPI and HRV sub-tabs
            
            # --- PPI Tab ---
            ppi_tab = QWidget()
            ppi_layout = QVBoxLayout()
            
            # Add a summary of the PPI results
            summary_text = f"Total peaks detected: {len(ppi_data)}\n"
            if 'PPI' in ppi_data.columns:
                summary_text += f"Average PPI: {ppi_data['PPI'].mean():.2f} ms\n"
                summary_text += f"Min PPI: {ppi_data['PPI'].min():.2f} ms\n"
                summary_text += f"Max PPI: {ppi_data['PPI'].max():.2f} ms\n"
                if 'Quality' in ppi_data.columns:
                    summary_text += f"Average signal quality: {ppi_data['Quality'].mean():.2f}\n"
            
            summary_label = QLabel(summary_text)
            ppi_layout.addWidget(summary_label)
            
            # If this was participant data, add participant information to the summary
            if 'Participant' in ppi_data.columns:
                participant_summary = "\nParticipant Information:\n"
                participants = ppi_data['Participant'].unique()
                participant_summary += f"Number of participants: {len(participants)}\n"
                participant_summary += f"Participants: {', '.join(participants)}\n"
                
                # Add epoch information if available
                if 'Epoch' in ppi_data.columns:
                    total_epochs = len(ppi_data.groupby(['Participant', 'Epoch']))
                    participant_summary += f"Total epochs: {total_epochs}\n"
                    
                    # Show epochs per participant (up to 5 participants to avoid cluttering)
                    if len(participants) <= 5:
                        for participant in participants:
                            participant_data = ppi_data[ppi_data['Participant'] == participant]
                            epochs = participant_data['Epoch'].unique()
                            participant_summary += f"  {participant}: {len(epochs)} epochs\n"
                
                participant_label = QLabel(participant_summary)
                ppi_layout.addWidget(participant_label)
            
            # Create a plot of the PPI values if available
            if 'PPI' in ppi_data.columns and len(ppi_data) > 1:
                plot_widget = pg.PlotWidget()
                plot_widget.setBackground('w')
                plot_widget.setTitle(f"PPI Values - {channel}")
                plot_widget.setLabel('left', 'PPI', units='ms')
                plot_widget.setLabel('bottom', 'Sample')
                
                # Plot PPI values
                pen = pg.mkPen(color=(76, 114, 176), width=2)
                plot_widget.plot(ppi_data['PPI'].dropna().values, pen=pen)
                
                ppi_layout.addWidget(plot_widget, 1)  # Give stretch factor
            
            ppi_tab.setLayout(ppi_layout)
            tab.addTab(ppi_tab, "PPI Data")
            
            # --- HRV Tab ---
            if hrv_metrics is not None and not hrv_metrics.empty:
                hrv_tab = QWidget()
                hrv_layout = QVBoxLayout()
                
                # Add HRV metrics summary (using overall metrics if available)
                overall_metrics = result_dict.get('overall_metrics')
                if overall_metrics is not None:
                    hrv_summary = "Overall HRV Metrics:\n"
                    hrv_summary += f"SDNN: {overall_metrics['SDNN']:.2f} ms\n"
                    hrv_summary += f"RMSSD: {overall_metrics['RMSSD']:.2f} ms\n"
                    hrv_summary += f"Mean HR: {60000 / overall_metrics['MeanNN']:.1f} bpm\n"
                    if 'Time_Range' in overall_metrics:
                        hrv_summary += f"Time Range: {overall_metrics['Time_Range']}\n"
                else:
                    hrv_summary = f"Windows analyzed: {len(hrv_metrics)}\n"
                    if not hrv_metrics.empty:
                        hrv_summary += f"Average SDNN: {hrv_metrics['SDNN'].mean():.2f} ms\n"
                        hrv_summary += f"Average RMSSD: {hrv_metrics['RMSSD'].mean():.2f} ms\n"
                        hrv_summary += f"Average HR: {60000 / hrv_metrics['MeanNN'].mean():.1f} bpm\n"
                
                hrv_summary_label = QLabel(hrv_summary)
                hrv_layout.addWidget(hrv_summary_label)
                
                # Add participant HRV information if available
                if 'Participant' in hrv_metrics.columns:
                    participant_hrv_summary = "\nParticipant HRV Information:\n"
                    participants = hrv_metrics['Participant'].unique()
                    
                    # Calculate average metrics per participant
                    participant_metrics = {}
                    for participant in participants:
                        p_data = hrv_metrics[hrv_metrics['Participant'] == participant]
                        participant_metrics[participant] = {
                            'SDNN': p_data['SDNN'].mean(),
                            'RMSSD': p_data['RMSSD'].mean(),
                            'MeanNN': p_data['MeanNN'].mean()
                        }
                    
                    # Display summary of metrics by participant (up to 5 to avoid cluttering)
                    if len(participants) <= 5:
                        for participant, metrics in participant_metrics.items():
                            participant_hrv_summary += f"  {participant} - SDNN: {metrics['SDNN']:.2f} ms, "
                            participant_hrv_summary += f"RMSSD: {metrics['RMSSD']:.2f} ms, "
                            participant_hrv_summary += f"HR: {60000 / metrics['MeanNN']:.1f} bpm\n"
                    else:
                        participant_hrv_summary += f"  {len(participants)} participants (too many to display individually)\n"
                    
                    participant_hrv_label = QLabel(participant_hrv_summary)
                    hrv_layout.addWidget(participant_hrv_label)
                
                # Create plots for common HRV metrics
                if len(hrv_metrics) > 1:
                    metrics_plot = pg.PlotWidget()
                    metrics_plot.setBackground('w')
                    metrics_plot.setTitle(f"HRV Metrics Over Time - {channel}")
                    metrics_plot.setLabel('left', 'Value', units='ms')
                    metrics_plot.setLabel('bottom', 'Window')
                    
                    # Convert timestamps to strings for x-axis
                    x_values = list(range(len(hrv_metrics)))
                    
                    # Plot SDNN
                    sdnn_pen = pg.mkPen(color=(76, 114, 176), width=2)
                    metrics_plot.plot(x_values, hrv_metrics['SDNN'].values, pen=sdnn_pen, name="SDNN")
                    
                    # Plot RMSSD
                    rmssd_pen = pg.mkPen(color=(214, 39, 40), width=2)
                    metrics_plot.plot(x_values, hrv_metrics['RMSSD'].values, pen=rmssd_pen, name="RMSSD")
                    
                    # Add legend
                    legend = metrics_plot.addLegend()
                    
                    hrv_layout.addWidget(metrics_plot, 1)
                    
                    # If participant data is available, also create a participant comparison plot
                    if 'Participant' in hrv_metrics.columns and len(participants) <= 5:
                        # Create a new plot that shows data grouped by participant
                        participant_plot = pg.PlotWidget()
                        participant_plot.setBackground('w')
                        participant_plot.setTitle(f"HRV Metrics by Participant - {channel}")
                        participant_plot.setLabel('left', 'Value', units='ms')
                        participant_plot.setLabel('bottom', 'Participant')
                        
                        # Use different colors for different metrics
                        colors = [(76, 114, 176), (221, 132, 82), (85, 168, 104), 
                                (196, 78, 82), (129, 114, 179)]
                        
                        # Create grouped bar chart-like visualization
                        bar_width = 0.2
                        
                        for p_idx, participant in enumerate(participants):
                            p_data = hrv_metrics[hrv_metrics['Participant'] == participant]
                            
                            # Plot SDNN bar
                            sdnn_mean = p_data['SDNN'].mean()
                            sdnn_bar = pg.BarGraphItem(
                                x=[p_idx - bar_width], height=[sdnn_mean], width=bar_width,
                                brush=colors[0 % len(colors)]
                            )
                            participant_plot.addItem(sdnn_bar)
                            
                            # Plot RMSSD bar
                            rmssd_mean = p_data['RMSSD'].mean()
                            rmssd_bar = pg.BarGraphItem(
                                x=[p_idx], height=[rmssd_mean], width=bar_width,
                                brush=colors[1 % len(colors)]
                            )
                            participant_plot.addItem(rmssd_bar)
                            
                            # If enough data points, manually add error bar lines instead of using ErrorBarItem
                            if len(p_data) > 1:
                                # For SDNN
                                sdnn_std = p_data['SDNN'].std()
                                
                                # Draw vertical line for SDNN error bar
                                sdnn_err_line = pg.PlotCurveItem(
                                    x=[p_idx - bar_width, p_idx - bar_width],
                                    y=[sdnn_mean - sdnn_std, sdnn_mean + sdnn_std],
                                    pen=pg.mkPen(color=colors[0 % len(colors)], width=2)
                                )
                                participant_plot.addItem(sdnn_err_line)
                                
                                # For RMSSD
                                rmssd_std = p_data['RMSSD'].std()
                                
                                # Draw vertical line for RMSSD error bar
                                rmssd_err_line = pg.PlotCurveItem(
                                    x=[p_idx, p_idx],
                                    y=[rmssd_mean - rmssd_std, rmssd_mean + rmssd_std],
                                    pen=pg.mkPen(color=colors[1 % len(colors)], width=2)
                                )
                                participant_plot.addItem(rmssd_err_line)
                        
                        # Add legend
                        legend = participant_plot.addLegend()
                        # Create proper dummy items for the legend
                        sdnn_dummy = pg.BarGraphItem(x=[0], height=[1], width=bar_width, brush=colors[0 % len(colors)])
                        rmssd_dummy = pg.BarGraphItem(x=[0], height=[1], width=bar_width, brush=colors[1 % len(colors)])
                        legend.addItem(sdnn_dummy, "SDNN")
                        legend.addItem(rmssd_dummy, "RMSSD")
                        
                        # Add participant labels to x-axis
                        axis = participant_plot.getAxis('bottom')
                        ticks = [(i, name) for i, name in enumerate(participants)]
                        axis.setTicks([ticks])
                        
                        hrv_layout.addWidget(participant_plot, 1)
                
                hrv_tab.setLayout(hrv_layout)
                tab.addTab(hrv_tab, "HRV Metrics")
            
            self.results_tabs.addTab(tab, channel)
        
        self.status_bar.showMessage("Processing complete")

    def save_results(self):
        """Save the processing results"""
        if not self.results:
            return

        # Get the directory to save results
        save_dir = QFileDialog.getExistingDirectory(self, "Select Directory to Save Results")

        if not save_dir:
            return

        # Determine input name for filename
        if self.file_radio.isChecked() and self.current_file:
            base_filename = os.path.splitext(os.path.basename(self.current_file))[0]
        elif self.directory_radio.isChecked() and self.current_directory:
            base_filename = os.path.basename(self.current_directory)
        elif self.participant_radio.isChecked() and self.current_directory:
            base_filename = "participant_analysis"
        else:
            base_filename = "ppg_analysis"

        try:
            for channel, result_dict in self.results.items():
                ppi_data = result_dict["ppi_data"]
                hrv_metrics = result_dict["hrv_metrics"]
                overall_metrics = result_dict.get("overall_metrics")

                if ppi_data.empty:
                    continue

                # Save PPI Data as CSV
                csv_path = os.path.join(save_dir, f"{base_filename}_{channel}_ppi.csv")
                ppi_data.to_csv(csv_path, index=False)

                # Save HRV metrics if available (both per-window and overall)
                if hrv_metrics is not None and not hrv_metrics.empty:
                    hrv_csv_path = os.path.join(save_dir, f"{base_filename}_{channel}_hrv.csv")

                    # If overall metrics exist, add them as a special row
                    if overall_metrics is not None:
                        # Convert overall metrics dict to DataFrame row
                        overall_df = pd.DataFrame([overall_metrics])
                        overall_df["Window"] = "Overall"  # Add identifier column

                        # Add window column to hrv_metrics if it doesn't exist
                        if "Window" not in hrv_metrics.columns:
                            hrv_metrics["Window"] = [f"Window_{i}" for i in range(len(hrv_metrics))]

                        # Combine per-window and overall metrics
                        combined_metrics = pd.concat([hrv_metrics, overall_df], ignore_index=True)
                        combined_metrics.to_csv(hrv_csv_path, index=False)
                    else:
                        hrv_metrics.to_csv(hrv_csv_path, index=False)

                # If participant data is available, also save aggregated metrics by participant
                if (
                    "Participant" in ppi_data.columns
                    and hrv_metrics is not None
                    and "Participant" in hrv_metrics.columns
                ):
                    participant_csv_path = os.path.join(save_dir, f"{base_filename}_{channel}_participant_summary.csv")

                    # Create summary dataframe grouped by participant
                    participant_summaries = []

                    for participant in hrv_metrics["Participant"].unique():
                        p_data = hrv_metrics[hrv_metrics["Participant"] == participant]

                        # Get number of epochs for this participant
                        num_epochs = 1
                        if "Epoch" in ppi_data.columns:
                            participant_ppi = ppi_data[ppi_data["Participant"] == participant]
                            num_epochs = len(participant_ppi["Epoch"].unique())

                        # Calculate summary metrics
                        summary = {
                            "Participant": participant,
                            "Epochs": num_epochs,
                            "Windows": len(p_data),
                            "SDNN_mean": p_data["SDNN"].mean(),
                            "SDNN_std": p_data["SDNN"].std(),
                            "RMSSD_mean": p_data["RMSSD"].mean(),
                            "RMSSD_std": p_data["RMSSD"].std(),
                            "MeanNN_mean": p_data["MeanNN"].mean(),
                            "HR_mean": 60000 / p_data["MeanNN"].mean(),
                            "DataPoints_mean": p_data["Num_Data_Points"].mean(),
                        }

                        participant_summaries.append(summary)

                    # Save participant summary
                    pd.DataFrame(participant_summaries).to_csv(participant_csv_path, index=False)

            QMessageBox.information(self, "Success", f"Results saved to {save_dir}")
            self.status_bar.showMessage(f"Results saved to {save_dir}")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save results: {str(e)}")
