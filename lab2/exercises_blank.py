# Exercises in order to perform laboratory work


# Import of modules
import numpy as np
import scipy.signal

from skimage.morphology import opening, closing


def load_vad_markup(path_to_rttm, signal, fs):
    # Function to read rttm files and generate VAD's markup in samples

    vad_markup = np.zeros(len(signal)).astype('float32')

    ###########################################################
    with open(path_to_rttm, 'r') as file:
        for line in file:
            parts = line.strip().split()
            
            start_time = float(parts[3])
            duration = float(parts[4])
            
            start_sample = int(start_time * fs)
            end_sample = int((start_time + duration) * fs)
            
            vad_markup[start_sample:end_sample] = 1
    ###########################################################

    return vad_markup

def framing(signal, window=320, shift=160):
    # Function to create frames from signal

    shape   = (int((signal.shape[0] - window)/shift + 1), window)
    frames  = np.zeros(shape).astype('float32')

    ###########################################################
    signal_length = len(signal)
    num_frames = int(np.ceil(float(np.abs(signal_length - window)) / shift))
    pad_signal_length = num_frames * shift + window
    z = np.zeros((pad_signal_length - signal_length))
    pad_signal = np.append(signal, z)

    w = np.hamming(window)
    frames = np.zeros((num_frames, window))
    for i in range(num_frames):
      start = i * shift
      end = start + window
      frames[i] = pad_signal[start:end] * w

    ###########################################################

    return frames

def frame_energy(frames):
    # Function to compute frame energies

    E = np.zeros(frames.shape[0]).astype('float32')

    ###########################################################
    E  = np.sum(frames, axis = 1)
    ###########################################################

    return E

def norm_energy(E):
    # Function to normalize energy by mean energy and energy standard deviation

    E_norm = np.zeros(len(E)).astype('float32')

    ###########################################################
    E_norm = (E - E.mean()) / (np.sqrt(E.var()))
    ###########################################################

    return E_norm

def gmm_train(E, gauss_pdf, n_realignment):
    # Function to train parameters of gaussian mixture model

    # Initialization gaussian mixture models
    w     = np.array([ 0.33, 0.33, 0.33])
    m     = np.array([-1.00, 0.00, 1.00])
    sigma = np.array([ 1.00, 1.00, 1.00])

    g = np.zeros([len(E), len(w)])
    for n in range(n_realignment):

        # E-step
        ###########################################################
        for k in range(len(w)):
            g[:, k] = w[k] * gauss_pdf(E, m[k], sigma[k])
        g = g / np.sum(g, axis=1, keepdims=True)
        ###########################################################

        # M-step
        ###########################################################
        N_k = np.sum(g, axis=0)

        w = N_k / len(E)

        m = np.sum(g * E[:, np.newaxis], axis=0) / N_k

        sigma = np.sqrt(np.sum(g * (E[:, np.newaxis] - m) ** 2, axis=0) / N_k)
        ###########################################################

    return w, m, sigma

def eval_frame_post_prob(E, gauss_pdf, w, m, sigma):
    # Function to estimate a posterior probability that frame isn't speech

    g0 = np.zeros(len(E))

    ###########################################################
    g = np.zeros(len(w))

    for i in range(len(E)):
      for k in range(len(w)):
          g[k] = w[k] * gauss_pdf(E[i], m[k], sigma[k])

      g0[i] = g[0] / np.sum(g)
    ###########################################################

    return g0

def energy_gmm_vad(signal, window, shift, gauss_pdf, n_realignment, vad_thr, mask_size_morph_filt):
    # Function to compute markup energy voice activity detector based of gaussian mixtures model

    # Squared signal
    squared_signal = signal**2

    # Frame signal with overlap
    frames = framing(squared_signal, window=window, shift=shift)

    # Sum frames to get energy
    E = frame_energy(frames)

    # Normalize the energy
    E_norm = norm_energy(E)

    # Train parameters of gaussian mixture models
    w, m, sigma = gmm_train(E_norm, gauss_pdf, n_realignment=10)

    # Estimate a posterior probability that frame isn't speech
    g0 = eval_frame_post_prob(E_norm, gauss_pdf, w, m, sigma)

    # Compute real VAD's markup
    vad_frame_markup_real = (g0 < vad_thr).astype('float32')  # frame VAD's markup

    vad_markup_real = np.zeros(len(signal)).astype('float32') # sample VAD's markup
    for idx in range(len(vad_frame_markup_real)):
        vad_markup_real[idx*shift:shift+idx*shift] = vad_frame_markup_real[idx]

    vad_markup_real[len(vad_frame_markup_real)*shift - len(signal):] = vad_frame_markup_real[-1]

    # Morphology Filters
    vad_markup_real = closing(vad_markup_real, np.ones(mask_size_morph_filt)) # close filter
    vad_markup_real = opening(vad_markup_real, np.ones(mask_size_morph_filt)) # open filter

    return vad_markup_real

def reverb(signal, impulse_response):
    # Function to create reverberation effect

    signal_reverb = np.zeros(len(signal)).astype('float32')

    ###########################################################
    signal_reverb = np.convolve(signal, impulse_response, mode='same')
    ###########################################################

    return signal_reverb

def awgn(signal, sigma_noise):
    # Function to add white gaussian noise to signal

    signal_noise = np.zeros(len(signal)).astype('float32')

    ###########################################################
    noise = np.random.normal(0, sigma_noise, len(signal))
    signal_noise = signal + noise
    ###########################################################

    return signal_noise
