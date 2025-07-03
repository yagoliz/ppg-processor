import os
from datetime import timedelta

import numpy as np
import pandas as pd


def calculate_ppi(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate PPI from a DataFrame containing timestamps

    Args:
        df (pd.DataFrame): DataFrame containing timestamps

    Returns:
        pd.DataFrame: DataFrame with PPI values calculated
    """
    df['PPI'] = df['Time'].diff().dt.total_seconds() * 1000  # Calculate time difference in milliseconds
    return df


def clean_ppi_data(df: pd.DataFrame, low: int = 667, high: int = 2000) -> pd.DataFrame:
    """
    Clean PPI data by removing rows with PPI values outside the valid range (667ms-2000ms)
    
    Args:
        df (pd.DataFrame): DataFrame containing PPI data
        low (float): Lower bound for valid PPI values
        high (float): Upper bound for valid PPI values

    Returns:
        pd.DataFrame: DataFrame with PPI data cleaned
    """

    # Drop rows where PPI is outside the valid range
    cleaned = df[(df['PPI'] >= low) & (df['PPI'] <= high)]
    print(f"Cleaned PPI data: Removed {len(df) - len(cleaned)} rows outside the range {low}ms-{high}ms.")

    return cleaned


# Define HRV metrics calculation
def calculate_metrics(ppi_data, quality_data):
    if len(ppi_data) < 2:
        # Return NaN for all metrics if there are insufficient data points
        return {
            "MeanNN": np.nan,
            "SDNN": np.nan,
            "RMSSD": np.nan,
            "SDSD": np.nan,
            "CVNN": np.nan,
            "CVSD": np.nan,
            "MedianNN": np.nan,
            "Num_Data_Points": len(ppi_data),  # Add count of data points
            "Mean_Quality": np.nan
        }

    mean_nn = np.mean(ppi_data)
    sdnn = np.std(ppi_data, ddof=1)
    rmssd = np.sqrt(np.mean(np.diff(ppi_data) ** 2))
    sdsd = np.std(np.diff(ppi_data), ddof=1)

    metrics = {
        "MeanNN": mean_nn,
        "SDNN": sdnn,
        "RMSSD": rmssd,
        "SDSD": sdsd,
        "CVNN": sdnn / mean_nn if mean_nn != 0 else np.nan,
        "CVSD": rmssd / mean_nn if mean_nn != 0 else np.nan,
        "MedianNN": np.median(ppi_data),
        "Num_Data_Points": len(ppi_data),  # Add count of data points
        "Mean_Quality": np.mean(quality_data)  # Add mean signal quality
    }
    return metrics


# Compute hrv metrics for each x-minute window
def calculate_hrv_metrics(data: pd.DataFrame, window: int = 5) -> pd.DataFrame:
    """
    Calculate HRV metrics from PPI data
    
    Args:
        data (pd.DataFrame): DataFrame containing columns "Time", "PPI", and "Quality"

    Returns:
        pd.DataFrame: DataFrame containing HRV metrics for each x-minute window
    """

    # Initialize variables
    hrv_results = []
    current_bin = []
    current_start_time = None

    for i, row in data.iterrows():
        if current_start_time is None:
            # Initialize the first n-minute bin
            current_start_time = row["Time"]

        # Check if row falls within the current n-minute bin
        if row["Time"] - current_start_time <= timedelta(minutes=window):
            
            # Check for gap larger than 1 minute
            if len(current_bin) > 0 and row["Time"] - current_bin[-1]["Time"] > timedelta(minutes=1):

                # Close the current bin due to a large gap
                if len(current_bin) > 1:
                    metrics = calculate_metrics(
                        [x["PPI"] for x in current_bin],
                        [x["Quality"] for x in current_bin]
                    )
                    metrics["Start_Time"] = current_start_time
                    metrics["End_Time"] = current_bin[-1]["Time"]
                    hrv_results.append(metrics)
                # Start a new bin
                current_bin = [{"Time": row["Time"], "PPI": row["PPI"], "Quality": row["Quality"]}]
                current_start_time = row["Time"]
            else:
                # Add row to the current bin
                current_bin.append({"Time": row["Time"], "PPI": row["PPI"], "Quality": row["Quality"]})
        else:
            # Bin exceeds 5 minutes, close it
            if len(current_bin) > 1:
                metrics = calculate_metrics(
                    [x["PPI"] for x in current_bin],
                    [x["Quality"] for x in current_bin]
                )
                metrics["Start_Time"] = current_start_time
                metrics["End_Time"] = current_bin[-1]["Time"]
                hrv_results.append(metrics)
            # Start a new bin
            current_bin = [{"Time": row["Time"], "PPI": row["PPI"], "Quality": row["Quality"]}]
            current_start_time = row["Time"]

    # Close the last bin
    if len(current_bin) > 1:
        metrics = calculate_metrics(
            [x["PPI"] for x in current_bin],
            [x["Quality"] for x in current_bin]
        )
        metrics["Start_Time"] = current_start_time
        metrics["End_Time"] = current_bin[-1]["Time"]
        hrv_results.append(metrics)

    # Save HRV results for the file
    return pd.DataFrame(hrv_results)