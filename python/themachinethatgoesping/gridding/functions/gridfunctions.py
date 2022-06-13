# SPDX-FileCopyrightText: 2022 Peter Urban, Ghent University
# SPDX-FileCopyrightText: 2022 GEOMAR Helmholtz Centre for Ocean Research Kiel
#
# SPDX-License-Identifier: MPL-2.0

"""
Helper functions for the gridder class, implemented using numba
"""

import math

import numba.types as ntypes
import numpy as np
from numba import njit, prange

from . import helperfunctions as hlp

# --- some usefull functions ---
@njit
def get_minmax(sx: np.array,
                   sy: np.array,
                   sz: np.array) -> tuple:
    """returns the min/max value of three lists (same size). 
    Sometimes faster than seperate numpy functions because it only loops once.

    Parameters
    ----------
    sx : np.array
        1D array with x positions (same size)
    sy : np.array
        1D array with x positions (same size)
    sz : np.array
        1D array with x positions (same size)

    Returns
    -------
    tuple
        with (xmin,xmax,ymin,ymax,zmin,zmax)
    """

    assert len(sx) == len(sy) == len(
        sz), "expected length of all arrays to be the same"

    minx = np.nan
    maxx = np.nan
    miny = np.nan
    maxy = np.nan
    minz = np.nan
    maxz = np.nan

    for i in range(len(sx)):
        x = sx[i]
        y = sy[i]
        z = sz[i]

        if not x > minx:
            minx = x
        if not x < maxx:
            maxx = x
        if not y > miny:
            miny = y
        if not y < maxy:
            maxy = y
        if not z > minz:
            minz = z
        if not z < maxz:
            maxz = z

    return minx, maxx, miny, maxy, minz, maxz

# --- static helper functions for the gridder (implemented using numba) ---


@njit
def get_index(val, grd_val_min, grd_res):
    return hlp.round_int((val - grd_val_min) / grd_res)


@njit
def get_index_fraction(val, grd_val_min, grd_res):
    return (val - grd_val_min) / grd_res


@njit
def get_value(index, grd_val_min, grd_res):
    return grd_val_min + grd_res * float(index)


@njit
def get_grd_value(value, grd_val_min, grd_res):
    return get_value(get_index(value, grd_val_min, grd_res), grd_val_min, grd_res)


@njit
def get_index_vals(fraction_index_x: float,
                   fraction_index_y: float,
                   fraction_index_z: float) -> (np.ndarray, np.ndarray, np.ndarray, np.ndarray):
    """
    Return a vector with fraction and weights for the neighboring grid cells.
    This allows for a linear interpolation (right?)
    :param fraction_index_x: fractional x index (e.g 4.2)
    :param fraction_index_y: fractional y index (e.g 4.2)
    :param fraction_index_z: fractional z index (e.g 4.2)
    :return: - vec X (x indices as int): all indices "touched" by the fractional point
             - vec Y (Y indices as int): all indices "touched" by the fractional point
             - vec Z (Z indices as int): all indices "touched" by the fractional point
             - vec Weights (Weights indices as int): weights
    """

    ifraction_x = fraction_index_x % 1
    ifraction_y = fraction_index_y % 1
    ifraction_z = fraction_index_z % 1

    fraction_x = 1 - ifraction_x
    fraction_y = 1 - ifraction_y
    fraction_z = 1 - ifraction_z

    ix1 = math.floor(fraction_index_x)
    ix2 = math.ceil(fraction_index_x)
    iy1 = math.floor(fraction_index_y)
    iy2 = math.ceil(fraction_index_y)
    iz1 = math.floor(fraction_index_z)
    iz2 = math.ceil(fraction_index_z)

    X = np.array([ix1, ix1, ix1, ix1, ix2, ix2, ix2, ix2])
    Y = np.array([iy1, iy1, iy2, iy2, iy1, iy1, iy2, iy2])
    Z = np.array([iz1, iz2, iz1, iz2, iz1, iz2, iz1, iz2])

    vx = 1 * fraction_x
    vxy = vx * fraction_y
    vxiy = vx * ifraction_y

    vix = 1 * ifraction_x
    vixy = vix * fraction_y
    vixiy = vix * ifraction_y

    WEIGHT = np.array([
        vxy * fraction_z,
        vxy * ifraction_z,
        vxiy * fraction_z,
        vxiy * ifraction_z,
        vixy * fraction_z,
        vixy * ifraction_z,
        vixiy * fraction_z,
        vixiy * ifraction_z
    ])

    return X, Y, Z, WEIGHT


@njit
def get_index_vals2_sup(fraction_index_x_min, fraction_index_x_max):
    ifraction_x_min = fraction_index_x_min % 1
    ifraction_x_max = fraction_index_x_max % 1
    fraction_x_min = 1 - ifraction_x_min
    fraction_x_max = 1 - ifraction_x_max

    if ifraction_x_min < 0.5:
        x1 = int(math.floor(fraction_index_x_min))
        fraction_x1 = 0.5 - ifraction_x_min
    else:
        x1 = int(math.ceil(fraction_index_x_min))
        fraction_x1 = 0.5 + fraction_x_min

    if fraction_x_max >= 0.5:
        x2 = int(math.floor(fraction_index_x_max))
        fraction_x2 = 0.5 + ifraction_x_max
    else:
        x2 = int(math.ceil(fraction_index_x_max))
        fraction_x2 = 0.5 - fraction_x_max

    length = x2 - x1 + 1

    X = np.empty((length)).astype(np.int64)
    W = np.ones((length)).astype(np.float64)

    W[0] = fraction_x1
    W[-1] = fraction_x2

    xm = (x1 + x2) / 2
    xl = (x2 - x1)

    for i, index in enumerate(range(x1, x2 + 1)):
        X[i] = index

    W /= np.sum(W)

    return X, W


# print(sum(WEIGHT))

@njit
def get_index_vals2(fraction_index_x_min, fraction_index_x_max,
                    fraction_index_y_min, fraction_index_y_max,
                    fraction_index_z_min, fraction_index_z_max):
    X_, WX_ = get_index_vals2_sup(fraction_index_x_min, fraction_index_x_max)
    Y_, WY_ = get_index_vals2_sup(fraction_index_y_min, fraction_index_y_max)
    Z_, WZ_ = get_index_vals2_sup(fraction_index_z_min, fraction_index_z_max)

    num_cells = X_.shape[0] * Y_.shape[0] * Z_.shape[0]

    X = np.empty((num_cells)).astype(np.int64)
    Y = np.empty((num_cells)).astype(np.int64)
    Z = np.empty((num_cells)).astype(np.int64)
    W = np.empty((num_cells)).astype(np.float64)

    i = 0
    for x, wx in zip(X_, WX_):
        for y, wy in zip(Y_, WY_):
            for z, wz in zip(Z_, WZ_):
                X[i] = x
                Y[i] = y
                Z[i] = z
                W[i] = wx * wy * wz

                i += 1

    return X, Y, Z, W


@njit()
def get_index_vals_inv_dist(x, xmin, xres,
                            y, ymin, yres,
                            z, zmin, zres,
                            R):
    norm_x = (x - xmin)
    norm_y = (y - ymin)
    norm_z = (z - zmin)

    ix_min = hlp.round_int((norm_x - R) / xres)
    ix_max = hlp.round_int((norm_x + R) / xres)
    iy_min = hlp.round_int((norm_y - R) / yres)
    iy_max = hlp.round_int((norm_y + R) / yres)
    iz_min = hlp.round_int((norm_z - R) / zres)
    iz_max = hlp.round_int((norm_z + R) / zres)

    # X = ntypes.List(ntypes.int64)
    # Y = ntypes.List(ntypes.int64)
    # Z = ntypes.List(ntypes.int64)
    # W = ntypes.List(ntypes.float64)
    X = []
    Y = []
    Z = []
    W = []

    min_dr = R / 10

    for ix in np.arange(ix_min, ix_max):
        dx = norm_x - ix * xres
        dx2 = dx*dx
        for iy in np.arange(iy_min, iy_max):
            dy = norm_y - iy * yres
            dy2 = dy*dy
            for iz in np.arange(iz_min, iz_max):
                dz = norm_z - iz * zres
                dz2 = dz*dz
                dr2 = dx2 + dy2 + dz2
                dr = math.sqrt(dr2)

                if dr <= R:
                    if dr < min_dr:
                        dr = min_dr
                    X.append(ix)
                    Y.append(iy)
                    Z.append(iz)
                    W.append(1/dr)

    X = np.array(X)
    Y = np.array(Y)
    Z = np.array(Z)
    W = np.array(W)

    #W /= np.nansum(W)

    return X, Y, Z, W


@njit()
def get_sampled_image_inv_dist(sx, sy, sz, sv,
                               xmin, xres, nx,
                               ymin, yres, ny,
                               zmin, zres, nz,
                               imagenum,
                               imagesum,
                               radius,
                               skip_invalid=True):

    for i in range(len(sx)):
        x = sx[i]
        y = sy[i]
        z = sz[i]
        v = sv[i]

        if i >= len(radius):
            print(len(radius), len(sx))
            raise RuntimeError('aaaah ')

        IX, IY, IZ, WEIGHT = get_index_vals_inv_dist(x, xmin, xres,
                                                     y, ymin, yres,
                                                     z, zmin, zres,
                                                     radius[i])

        # for ix,iy,iz,w in zip(IX,IY,IZ,WEIGHT):
        for i_ in range(len(IX)):
            ix = int(IX[i_])
            iy = int(IY[i_])
            iz = int(IZ[i_])
            w = WEIGHT[i_]

            if w == 0:
                continue

            if not skip_invalid:
                if ix < 0:
                    ix = 0
                if iy < 0:
                    iy = 0
                if iz < 0:
                    iz = 0

                if abs(ix) >= nx:
                    ix = nx - 1
                if abs(iy) >= ny:
                    iy = ny - 1
                if abs(iz) >= nz:
                    iz = nz - 1
            else:
                if ix < 0:
                    continue
                if iy < 0:
                    continue
                if iz < 0:
                    continue

                if abs(ix) >= nx:
                    continue
                if abs(iy) >= ny:
                    continue
                if abs(iz) >= nz:
                    continue

            # print(ix,iy,iz,v,w)
            if v >= 0:
                imagesum[ix][iy][iz] += v * w
                imagenum[ix][iy][iz] += w

    return imagesum, imagenum


#@njit(parallel = True)
@njit()
def get_sampled_image2(sx: np.array, sy: np.array, sz: np.array, sv: np.array,
                       xmin, xres, nx,
                       ymin, yres, ny,
                       zmin, zres, nz,
                       imagenum,
                       imagesum,
                       extent=None,
                       skip_invalid=True):

    for i in range(len(sx)):
        x = sx[i]
        y = sy[i]
        z = sz[i]
        v = sv[i]

        if extent is None:
            IX, IY, IZ, WEIGHT = get_index_vals(
                get_index_fraction(x, xmin, xres),
                get_index_fraction(y, ymin, yres),
                get_index_fraction(z, zmin, zres)
            )
        else:
            if i >= len(extent):
                print(len(extent), len(sx))
                raise RuntimeError('aaaah ')

            length_2 = extent[i] / 2

            IX, IY, IZ, WEIGHT = get_index_vals2(
                get_index_fraction(
                    x - length_2, xmin, xres), get_index_fraction(x + length_2, xmin, xres),
                get_index_fraction(
                    y - length_2, ymin, yres), get_index_fraction(y + length_2, ymin, yres),
                get_index_fraction(
                    z - length_2, zmin, zres), get_index_fraction(z + length_2, zmin, zres)
            )

        # for ix,iy,iz,w in zip(IX,IY,IZ,WEIGHT):
        for i_ in range(len(IX)):
            ix = int(IX[i_])
            iy = int(IY[i_])
            iz = int(IZ[i_])
            w = WEIGHT[i_]

            if w == 0:
                continue

            if not skip_invalid:
                if ix < 0:
                    ix = 0
                if iy < 0:
                    iy = 0
                if iz < 0:
                    iz = 0

                if abs(ix) >= nx:
                    ix = nx - 1
                if abs(iy) >= ny:
                    iy = ny - 1
                if abs(iz) >= nz:
                    iz = nz - 1
            else:
                if ix < 0:
                    continue
                if iy < 0:
                    continue
                if iz < 0:
                    continue

                if abs(ix) >= nx:
                    continue
                if abs(iy) >= ny:
                    continue
                if abs(iz) >= nz:
                    continue

            # print(ix,iy,iz,v,w)
            if v >= 0:
                imagesum[ix][iy][iz] += v * w
                imagenum[ix][iy][iz] += w

    return imagesum, imagenum


@njit
def get_sampled_image(sx, sy, sz, sv,
                      xmin, xres, nx,
                      ymin, yres, ny,
                      zmin, zres, nz,
                      imagenum,
                      imagesum,
                      skip_invalid=True):

    for i in range(len(sx)):
        x = sx[i]
        y = sy[i]
        z = sz[i]
        v = sv[i]

        ix = get_index(x, xmin, xres)
        iy = get_index(y, ymin, yres)
        iz = get_index(z, zmin, zres)

        if not skip_invalid:
            if ix < 0:
                ix = 0
            if iy < 0:
                iy = 0
            if iz < 0:
                iz = 0

            if abs(ix) >= nx:
                ix = nx - 1
            if abs(iy) >= ny:
                iy = ny - 1
            if abs(iz) >= nz:
                iz = nz - 1
        else:
            if ix < 0:
                continue
            if iy < 0:
                continue
            if iz < 0:
                continue

            if abs(ix) >= nx:
                continue
            if abs(iy) >= ny:
                continue
            if abs(iz) >= nz:
                continue

        if v >= 0:
            imagesum[ix][iy][iz] += v
            imagenum[ix][iy][iz] += 1

    return imagesum, imagenum
