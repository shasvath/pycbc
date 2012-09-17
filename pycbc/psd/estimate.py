#!/usr/bin/python
# Copyright (C) 2012 Tito Dal Canton
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 2 of the License, or (at your
# option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General
# Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
""" Utilites to estimate PSDs from data. """

import numpy
from pycbc.types import Array, FrequencySeries
from pycbc.fft import fft, ifft

def median_bias(n):
    """
    Return the bias of the median average PSD computed from n segments.
    See arXiv:gr-qc/0509116 appendix B for details.
    """
    if n >= 1000:
        return numpy.log(2)
    ans = 1
    for i in xrange(1, (n - 1) / 2 + 1):
        ans += 1.0 / (2*i + 1) - 1.0 / (2*i)
    return ans

def welch(timeseries, seg_len=4096, seg_stride=2048, window='hann', \
                            avg_method='median', max_filter_len=None):
    """
    Estimate the PSD of a timeseries using Welch's method.
    See arXiv:gr-qc/0509116 for details.
    """
    window_map = {
        'hann': numpy.hanning
    }
    if not window in window_map:
        raise ValueError('Invalid window')
    if not avg_method in ('mean', 'median', 'median-mean'):
        raise ValueError('Invalid averaging method')
    num_samples = len(timeseries)
    num_segments = num_samples / seg_stride
    if (num_segments - 1) * seg_stride + seg_len > num_samples:
        num_segments -= 1
    if num_samples != (num_segments - 1) * seg_stride + seg_len:
        raise ValueError('Incorrect choice of segmentation parameters')
    w = Array(window_map[window](seg_len).astype(timeseries.dtype))
    # calculate psd of each segment
    delta_f = 1. / timeseries.delta_t / seg_len
    segment_tilde = FrequencySeries(numpy.zeros(seg_len / 2 + 1), \
        delta_f=delta_f, dtype=numpy.complex128)
    segment_psds = []
    for i in xrange(num_segments):
        segment_start = i * seg_stride
        segment_end = segment_start + seg_len
        segment = timeseries[segment_start:segment_end]
        assert len(segment) == seg_len
        fft(segment * w, segment_tilde)
        segment_psds.append(abs(segment_tilde * segment_tilde.conj()))
    # calculate average psd
    if avg_method == 'mean':
        psd = numpy.mean(segment_psds, axis=0)
    elif avg_method == 'median':
        psd = numpy.median(segment_psds, axis=0) / median_bias(num_segments)
    elif avg_method == 'median-mean':
        odd_psds = segment_psds[::2]
        even_psds = segment_psds[1::2]
        odd = numpy.median(odd_psds, axis=0) / median_bias(len(odd_psds))
        even = numpy.median(even_psds, axis=0) / median_bias(len(even_psds))
        psd = numpy.mean([odd, even], axis=0)
    psd *= 2 * delta_f * seg_len / numpy.sum(numpy.square(w))
    # TODO coarse graining
    return FrequencySeries(psd, delta_f=delta_f, dtype=timeseries.dtype)
