import numpy as np

from hmtk.catalogue.declusterer.base import BaseCatalogueDecluster
from hmtk.catalogue.declusterer.utils import decimal_year, haversine

class GardnerKnopoffType1(BaseCatalogueDecluster):
    '''Gardner Knopoff algorithm'''
    
    def decluster(self, catalogue, config):
        """
        :param catalogue: Catalogue of earthquakes
        :type catalogue: Dictionary
        :param config: Configation parameters
        :type config: Dictionary

        :returns: 
          **vcl vector** indicating cluster number, 
              **flagvector** indicating which eq events belong to a cluster
        :rtype: numpy.ndarray
        """

        # Get relevent parameters
        neq = len(catalogue['magnitude'])  # Number of earthquakes
        # Get decimal year (needed for time windows)
        year_dec = decimal_year(
            catalogue['year'], catalogue['month'], catalogue['day'])
        # Get space and time windows corresponding to each event
        sw_space, sw_time = (
            config['time_distance_window'].calc(catalogue['magnitude']))
        # Initial Position Identifier
        eqid = np.arange(0, neq, 1)  
        # Pre-allocate cluster index vectors
        vcl = np.zeros(neq, dtype=int)
        # Sort magnitudes into descending order
        id0 = np.flipud(np.argsort(catalogue['magnitude'], kind='heapsort'))
        #mag = catalogue['magnitude'][id0]
        longitude = catalogue['longitude'][id0]
        latitude = catalogue['latitude'][id0]
        sw_space = sw_space[id0]
        sw_time = sw_time[id0]
        year_dec = year_dec[id0]
        eqid = eqid[id0]
        flagvector = np.zeros(neq, dtype=int)
        # Begin cluster identification
        clust_index = 0
        for i in range(0, neq - 1):
            if vcl[i] == 0:
                # Find Events inside both fore- and aftershock time windows
                dt = year_dec - year_dec[i]
                vsel = np.logical_and(
                    dt >= (-sw_time[i] * config['fs_time_prop']),
                    dt <= sw_time[i], 
                    flagvector == 0)
                # Of those events inside time window, find those inside distance
                # window
                vsel1 = haversine(longitude, latitude, longitude[i], 
                                  latitude[i]) <= sw_space[i]
                vsel[vsel] = vsel1
                temp_vsel = np.copy(vsel)
                temp_vsel[i] = False
                if any(temp_vsel):
                    # Allocate a cluster number
                    vcl[vsel] = clust_index + 1
                    flagvector[vsel] = 1
                    # For those events in the cluster before the main event,
                    # flagvector is equal to -1
                    temp_vsel[dt >= 0.0] = False
                    flagvector[temp_vsel] = -1
                    flagvector[i] = 0
                    clust_index += 1

        # Re-sort the catalog_matrix into original order
        id1 = np.argsort(eqid, kind='heapsort')
        eqid = eqid[id1]
        vcl = vcl[id1]
        flagvector = flagvector[id1]
        
        return vcl, flagvector

def _find_aftershocks(dtime, nval, time_window):
    """
    Searches for aftershocks within the moving
    time window
    :param dtime: time since main event
    :type dtime: numpy.ndarray
    :param nval: number of events in search window
    :type nval: int
    :param time_window: Length (in days) of moving time window
    :type time_window: positive float
    :returns: **vsel** index vector for aftershocks
    :rtype: numpy.ndarray
    """

    vsel = np.array(np.ones(nval), dtype=bool)
    initval = dtime[0]  # Start with the mainshock

    j = 1
    while j < nval:
        ddt = dtime[j] - initval
        # Is event after previous event and within time window?
        vsel[j] = np.logical_and(ddt >= 0.0, ddt <= time_window)
        if vsel[j]:
            # Reset time window to new event time
            initval = dtime[j]
        j += 1
    return vsel


def _find_foreshocks(dtime, nval, time_window, vsel_aftershocks):
    """
    Searches for foreshocks within the moving
    time window
    :param dtime: time since main event
    :type dtime: numpy.ndarray
    :param nval: number of events in search window
    :type nval: int
    :param time_window: Length (in days) of moving time window
    :type time_window: positive float
    :param vsel_aftershocks: index vector for aftershocks
    :type vsel_aftershocks: numpy.ndarray
    :returns: **vsel** index vector for foreshocks
    :rtype: numpy.ndarray
    """

    j = 1
    vsel = np.array(np.zeros(nval), dtype=bool)
    initval = dtime[0]

    while j < nval:
        if vsel_aftershocks[j]:
        # Event already allocated as an aftershock - skip
            j += 1
        else:
            ddt = dtime[j] - initval
            # Is event before previous event and within time window?
            vsel[j] = np.logical_and(ddt <= 0.0,
                                      ddt >= -(time_window))
            if vsel[j]:
            # Yes, reset time window to new event
                initval = dtime[j]
        j += 1

    return vsel