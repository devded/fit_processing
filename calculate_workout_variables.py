from bs4 import BeautifulSoup
import numpy as np 
PI = np.pi
import csv
import os
from collections import OrderedDict
import re

OUTPUT_FILE = 'gpx_processed_info.csv' 

MAX_SPEED = 50#mph

#radius of earth in miles
C_R = 6371/1.60934
def distcalc(c1, c2):
    lat1 = float(c1['lat'])*PI/180.
    lon1 = float(c1['lon'])*PI/180.

    lat2 = float(c2['lat'])*PI/180.
    lon2 = float(c2['lon'])*PI/180.

    dlat = lat2-lat1
    dlon = lon2-lon1

    a = np.sin(dlat/2.)**2 + np.cos(lat1)*np.cos(lat2)*np.sin(dlon/2)**2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))
    return C_R * c 

def calculate_distances(points):
    return np.asarray(
        [
            distcalc(c2.attrs, c1.attrs)
            for c1, c2 in zip(points[1:], points[:-1])
        ]
    ) 

def calculate_velocities(distances):
    return distances * 3600 

def calculate_accelerations(velocities):
    return np.diff(velocities)

MIPS_TO_MPH = 3600.

FPS_TO_MPH = 3600./5280

G_FPS = 32.

G_MPHPS = 32 * FPS_TO_MPH

def process_file(filename, target_dir):
    new_filename = re.sub(r'([^.]+)\.gpx', r'raw_csv/\1.csv', filename)
    if os.path.exists(new_filename):
        #print '%s already exists. skipping.' % new_filename
        return None
    print(f'processing {filename}')
    with open(os.path.join(target_dir, filename),'r') as f:
        soup = BeautifulSoup(f.read(), 'lxml')
        track = soup.find('trk')
        segments = track.find('trkseg')
        points = segments.find_all('trkpt')
        times = [p.find('time').text for p in points]
        elevations = np.asarray([float(p.find('ele').text) for p in points])
    #lon-lat based
    distances = calculate_distances(points)
    velocities = calculate_velocities(distances)
    #if velocity > MAX_SPEED, then it indicates discontinuity
    velocities = velocities * (velocities < MAX_SPEED)
    accelerations = calculate_accelerations(velocities)
    #elevation
    elevation_changes = np.diff(elevations)
    sum_v = np.sum(velocities)
    sum_v2 = np.sum(velocities**2)
    sum_v3 = np.sum(velocities**3)
    abs_elevation = np.sum(np.abs(elevation_changes))/2
    sum_a = np.sum(accelerations * (accelerations > 0))
    #alternative type of accelerations measurement
    velocities_mph = 3600 * velocities
    energy_increases = velocities_mph[1:]**2 - velocities_mph[:-1]**2
    energy_increases = energy_increases - FPS_TO_MPH**2 * G_FPS * elevation_changes[1:] * (elevation_changes[1:] < 0)
    energy_increases = np.sum(energy_increases * (energy_increases > 0))
    with open(new_filename, 'w') as f:
        f.write('time,distance,elevation_change')
        for t, d, e in zip(times[1:], distances, elevation_changes):
            f.write('\n')
            f.write(','.join([str(t), str(d), str(e)]))
            return {
                'sum_v':sum_v,
                'sum_v2':sum_v2,
                'abs_elevation':abs_elevation,
                'sum_a':sum_a,
                'sum_v3':sum_v3,
                'sum_e':energy_increases
            }

def main(gpx_source_dir, gpx_target_dir, gpx_summary_filename):
    original_dir = os.getcwd()
    os.makedirs(gpx_target_dir, exist_ok=True)

    os.chdir(gpx_source_dir)
    file_list = [x for x in os.listdir('.') if x[-4:].lower()=='.gpx']
    file_list.sort()
    fileinfo = OrderedDict()
    for file in file_list:
        td = process_file(file, gpx_target_dir)
        if td is not None: 
            fileinfo[file] = td
    return 0


if __name__=='__main__':
    raise NotImplementedError('this program is now to be called from other files') #main()
