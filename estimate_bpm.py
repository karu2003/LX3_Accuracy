import wave
import struct
import numpy as np
from scipy import signal
import pywt
import pylab as plt

class BPM_Analyzer:
    def __init__(self,
        levels = 5):
        self.empty = False
        self.axs = []
        self.fig = []
        self.st = 'sym5' #'sym5' 'db4'
        self.levels = levels

    def lepow2(self,x):    
        return int(2 ** np.floor(np.log2(x)))

    def normalize(self,data):
        amp = 32767/np.max(np.abs(data))
        mean = np.mean(data)
        norm = [(data[i] - mean) * amp for i, k in enumerate(data)]
        return norm          

    def extractDWTCoefficients(self,data, deg=4):
        """
        Before we get into computing the window bpm, let's figure out exactly what the DWT is.
        Those familiar with signal processing will know the Fourier Transform, which decomposes a
        signal into its constituents. On a high level, the DWT does a similar decomposition, but only
        into high-frequency and low-frequency components, while maintaining when these frequencies occur.
        These are stored in the detail coefficients (dC) and approximation coefficients (aC) respectively.
        By performing cascading DWTs on the approximation coefficients, we can recover finer frequency resolution,
        which is what we want for a good frequency decomposition:
        https://en.wikipedia.org/wiki/Discrete_wavelet_transform#Cascading_and_filter_banks
        """
        dC_list, aC_list = [], []
        for i in range(deg):
            # We use the 4 coefficient Daubechies wavelets because the paper says so
            aC, dC = pywt.dwt(data, self.st, 'smooth') 
            # The length of each cascading transform is approximately halved
            dC_list.append(dC)
            # Here's why: http://www.pybytes.com/pywavelets/ref/dwt-discrete-wavelet-transform.html#single-level-dwt
            aC_list.append(aC)
            data = aC
        return dC_list, aC_list

    def detectPeak(self,data):
        """
        All we're doing here is determining the index of the largest magnitude datum
        in the supplied data. This is needed later for determining the index of beats
        in a window. (Full disclosure, I just copied this part verbatim from Scaperot)
        """
        max_val = np.amax(abs(data))
        peak_ndx = np.where(data == max_val)
        if len(peak_ndx[0]) == 0:
            peak_ndx = np.where(data == -max_val)
        return peak_ndx

    def wavedec_n(self,data):
        coeffs = pywt.wavedec(data, self.st, level=self.levels)
        dCs = coeffs[1:5]
        return dCs[::-1]

    def downcoef_n(self,data):
        aC = pywt.downcoef('a', data, self.st, level=self.levels)
        dC = pywt.downcoef('d', data, self.st, level=self.levels)
        return dC, aC

    def max_level(self,data):
        level = pywt.dwt_max_level(len(data), self.st)
        return level

    def computeWindowBPM(self,data, framerate):
        """
        Finally, the real meat of the process: computing the bpm of a sound window.
        I'll annotate step-by-step and try to correlate the steps with the paper
        linked above.
        """
        # 0) Extract DWTs
        # We're going to need the high frequency decomposition (dCs)
        # dCs = self.wavedec_n(data)
        dCs, aCs = self.extractDWTCoefficients(data, self.levels)
 
        # 0.5 ) Extract relevant variables
        # This will be useful later for downsampling and calculating the final bpm
        max_downsample = 2**(self.levels - 1)
  
        # We'll use this later to ensure the size of each window is the same during computation
        coeff_minlen = int(len(dCs[0])/max_downsample)
      
        # Here we define the upper and lower bounds for tempos our program can find.
        # 220bpm = upper bound, 40bpm = lower bound
        min_idx = int(60. / 220 * (framerate/max_downsample))
        max_idx = int(60. / 40 * (framerate/max_downsample))

        # 1) Low Pass Filter (LPF)
        # A low pass filter cleans up the noise at each frequency band
        dCs = [signal.lfilter([0.01], [1 - 0.99], dC) for dC in dCs]

        # 2) Full Wave Rectification (FWR)
        # We want to make sure our signal values are >= 0
        dCs = [abs(dC) for dC in dCs]

        # 3) Downsampling (DOWN) 
        # Remember how the size of each frequency band is roughly half the previous? Downsampling roughly equivocates the length of the bands
        # dCs = [dC[::2**(self.levels - 1 - i)] for i, dC in enumerate(dCs)]
        # dCs = [dC[::2**(self.levels - 2 - i)] for i, dC in enumerate(dCs)] # use for wavedec_n
        dCs = [signal.resample(dCs[i], len(dCs[3])) for i in range(len(dCs))]
      
        # 4) Normalization (NORM)
        # for i, dC in enumerate(dCs):
        #     mean = np.mean(dC)
        #     # Normalize the data just by subtracting the mean
        #     dCs[i] = dC - mean

        for i in range(len(dCs)):
            dCs[i] = self.normalize(dCs[i])

        # 5) Autocorrelation (ACRL)
        # We're going to perform the autocorrelation on the summation of each band
        # dC_sum = np.zeros([coeff_minlen])
        # for dC in dCs:
        #     # To sum the bands up, each length needs to be exactly the same. Here's where coeff_minlen is handy!
        #     dC_sum += dC[:coeff_minlen]
        # # We're looking for pattern similarities at different times, which correspond to beats!

        # dC_sum = np.zeros(len(dCs[0]))
        # for dC in dCs:
        #     dC_sum += dC

        # dC_sum = np.zeros(len(dCs[0]))
        # for dC in dCs:
        #     dC_sum = sum(dC_sum,dC)

        dC_sum = np.median(dCs, axis=0) 

        correlation = np.correlate(dC_sum, dC_sum, 'full')

        # The autocorrelation is symmetric, so we only need the latter half
        correlation_half = correlation[int(len(correlation)/2):]
        correlation_frame = correlation_half[min_idx:max_idx]

        peak_idx = self.detectPeak(correlation_frame)[0] + min_idx
        # # Just like when we were determining the bounds, we can use the same formula to determine the bpm

        bpm = 60. / peak_idx * (framerate/max_downsample)

        return correlation_frame, bpm

    def plot_date(self,data):
    
        color = ['r', 'g', 'b', '#487bb7', '#548fc0', # '#00429d', '#2754a6', '#3a67ae'
                '#5ea3c9', '#66b8d3', '#6acedd', '#68e5e9', '#ffe2ca', 
                '#ffc4b4', '#ffa59e', '#f98689', '#ed6976', '#dd4c65', 
                '#ca2f55', '#b11346', '#93003a']

        counts = len(data)
        #print('counts are: %s' % (counts))
        if not self.empty:
            if counts == 1:
                self.fig, self.axs = plt.subplots()
                self.fig.suptitle('Axes values are scaled individually by default')
                self.empty = True
            else:
                self.fig, self.axs = plt.subplots(counts)
                self.fig.suptitle('Axes values are scaled individually by default')
                self.empty = True

        for i in range (counts):
            if counts == 1:
                self.axs.cla()
                self.axs.plot(data[i], color[i])
            else:    
                self.axs[i].cla()
                self.axs[i].plot(data[i], color[i])

        plt.tight_layout()    
        #plt.ion()
        plt.pause(0.001)
        plt.show()
        return

    def s_plot(self,data):
        fig, ax = plt.subplots(figsize=(6,1))
        ax.set_title("Data: ")
        ax.plot(data)
        plt.show()

    def plot_peak(self,x,peaks,properties):     
        plt.plot(x)
        plt.plot(peaks, x[peaks], "x")
        plt.vlines(x=peaks, ymin=x[peaks] - properties["prominences"], ymax = x[peaks], color = "C1")
        plt.hlines(y=properties["width_heights"], xmin=properties["left_ips"], xmax=properties["right_ips"], color = "C1")
        plt.show()        

