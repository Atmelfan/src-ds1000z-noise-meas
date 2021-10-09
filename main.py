from time import sleep

from ds1054z import DS1054Z
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import matplotlib.mlab as mlab
import scipy.fftpack
from numpy import mean

import argparse

parser = argparse.ArgumentParser(description="Noise measurement utility")
parser.add_argument("scope", metavar="IP|VISA", type=str,
                    help="IP or VISA resource string to instrument")
parser.add_argument("-c", "--channel", metavar="CH", type=int, default=1,
                    help="Oscilloscope channel to measure on")
parser.add_argument("-s", "--scale", type=float, default=1.0e-3,
                    help="Oscilloscope vertical scale")
parser.add_argument("-C", "--coupling", type=str, choices=["DC", "AC"], default="DC",
                    help="DC or AC coupling")
parser.add_argument("-g", "--gain", type=float, default=100e3,
                    help="Pre-amplifier/setup gain")


def sample(scope):
    # Acquire
    scope.single()
    status = "Potato"
    while status.lower() != "stop":
        status = scope.query("TRIG:STAT?")
        # print(f"status = {status}")
        sleep(1)
    wave = np.array(scope.get_waveform_samples(args.channel)) * (1.0 / args.gain)
    return wave, (max(wave) - min(wave))


if __name__ == '__main__':
    args = parser.parse_args()

    scope = DS1054Z('192.168.100.64')
    print(scope.idn)
    scope.clear()
    scope.stop()

    # Setup
    scope.display_only_channel(args.channel)
    scope.set_probe_ratio(args.channel, 1.0)
    scope.set_channel_scale(args.channel, args.scale, True)
    scope.timebase_scale = 1.0
    scope.write("ACQ:TYPE HRES")
    scope.write(f"CHAN{args.channel}:COUP {args.coupling.upper()}")
    # scope.sample_rate = 100

    N = 10
    wave = np.array([])
    vpp = np.array([])
    for x in range(0, N):
        print(f"Sampling ({x + 1}/{N})")
        samples, _vpp = sample(scope)
        wave = np.append(wave, samples)
        vpp = np.append(vpp, _vpp)
    wave = wave - mean(wave)
    scope.close()

    # Vpp
    vpp_mean = mean(vpp) * 1.0e9

    # FFT
    T = 12 * N * 1.0 / len(wave)  # Doesn't work,
    print(f"T={T}, N={len(wave)}")
    x = np.linspace(0.0, len(wave) * T, len(wave))

    # Plot
    fig, (ax0, ax1) = plt.subplots(2, 1)
    ax0.set_title(f"0.1-Hz to 10-Hz Noise\n{scope.idn}")

    ax0.plot(x, wave * 1e9)
    ax0.plot([], [], ' ', label=r"Avg: ${:.2f} nV_{{P-P}}$, Max: ${:.2f} nV_{{P-P}}$, Min:${:.2f} nV_{{P-P}}$, ".format(
        mean(vpp) * 1e9, max(vpp) * 1e9, min(vpp) * 1e9))
    ax0.plot([], [], ' ', label=r"Pre-amplifier gain = {:.1e}".format(args.gain))
    ax0.set_ylabel("Voltage [$nV$]")
    ax0.set_xlabel("Time [$s$]")
    ax0.xaxis.set_major_formatter(mticker.ScalarFormatter())
    ax0.xaxis.set_minor_formatter(mticker.NullFormatter())
    ax0.legend()

    Pxx, freqs = mlab.psd(wave, 64, 1 / T)
    ax1.loglog(freqs, np.sqrt(Pxx) * 1e9)
    ax1.set_ylabel("Voltage noise density [$nV/\sqrt{Hz}$]")
    ax1.set_xlabel("Frequency [$Hz$]")
    ax1.xaxis.set_major_formatter(mticker.ScalarFormatter())
    ax1.xaxis.set_minor_formatter(mticker.NullFormatter())
    ax1.yaxis.set_major_formatter(mticker.ScalarFormatter())
    ax1.yaxis.set_minor_formatter(mticker.NullFormatter())
    ax1.grid()

    plt.show()
