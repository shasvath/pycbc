# Copyright (C) 2012  Alex Nitz
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 3 of the License, or (at your
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


#
# =============================================================================
#
#                                   Preamble
#
# =============================================================================
#
import numpy, pycbc
from pycbc.opt import omp_libs, omp_flags
from scipy.weave import inline
from .simd_correlate import correlate_parallel, default_segsize, corr_parallel_code, corr_support
from .matchedfilter import _BaseCorrelator
import sys

support = """
    #include <stdio.h>
    #include <math.h>
"""

def correlate_numpy(x, y, z):
    z.data[:] = numpy.conjugate(x.data)[:]
    z *= y
    
code = """
#pragma omp parallel for
for (int i=0; i<N; i++){
    TYPE xr, yr, xi, yi, re, im;
    xr = xa[i].real();
    xi = xa[i].imag();
    yr = ya[i].real();       
    yi = ya[i].imag();

    re = xr*yr + xi*yi;
    im = xr*yi - xi*yr;

    za[i] = std::complex<TYPE>(re, im);
}
"""
single_code = code.replace('TYPE', 'float')
double_code = code.replace('TYPE', 'double')

def correlate_inline(x, y, z):
    if z.precision == 'single':
        the_code = single_code
    else:
        the_code = double_code
        
    za = numpy.array(z.data, copy=False)
    xa = numpy.array(x.data, copy=False)
    ya = numpy.array(y.data, copy=False)
    N = len(x) 
    inline(the_code, ['xa', 'ya', 'za', 'N'], 
                    extra_compile_args=['-march=native -O3 -w'] + omp_flags,
                    support_code = support,
                    libraries=omp_libs
          )
    
#correlate = correlate_inline
correlate = correlate_parallel   

class CPUCorrelator(_BaseCorrelator):
    def __init__(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z
        self.arrlen = len(self.x)
        self.code = corr_parallel_code
        self.support = corr_support
        self.segsize = default_segsize

    def correlate(self):
        htilde = self.x
        stilde = self.y
        qtilde = self.z
        arrlen = self.arrlen
        segsize = self.segsize
        inline(self.code, ['htilde', 'stilde', 'qtilde', 'arrlen', 'segsize'],
               extra_compile_args = ['-march=native -O3 -w'] + omp_flags,
               #extra_compile_args = ['-mno-avx -mno-sse2 -mno-sse3 -mno-ssse3 -mno-sse4 -mno-sse4.1 -mno-sse4.2 -mno-sse4a -O2 -w'] + omp_flags,
               #extra_compile_args = ['-msse3 -O3 -w'] + omp_flags,
               libraries = omp_libs, support_code = self.support, auto_downcast = 1)
 
        
def _correlate_factory(x, y, z):
    return CPUCorrelator
