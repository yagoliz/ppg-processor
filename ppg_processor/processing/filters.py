import numpy as np
from scipy.signal import butter, sosfiltfilt

def bandpass_filter(
    s: np.ndarray, lowcut: float, highcut: float, fs: float, order: int = 5
) -> np.ndarray:
    """
    Apply a Butterworth bandpass filter to the signal.

    ### Args:
    - signal (np.ndarray): Array-like, the signal to be filtered.
    - lowcut (float): The low cutoff frequency of th filter.
    - highcut (float): The high cutoff frequency of th filter.
    - fs (int): Sampling frequency of the signal
    - order (int): Order of the filter

    ### Returns:
    Array-like, the filtered signal.

    ### Example:

      >>> import numpy as np
      >>> data = np.random(100)
      >>> lc = 2.0
      >>> hc = 10.5
      >>> fs = 50.0
      >>> filtered_data = highpass_filter(data, lc, hc, fs, order=5)

    """
    nyq = 0.5 * fs
    low = lowcut / nyq
    high = highcut / nyq
    sos = butter(order, [low, high], btype="bandpass", output="sos")
    y = sosfiltfilt(sos, s)
    return y