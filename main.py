import json,h5py
from scripts.data import get_mask,get_data,get_altitude_data,get_meta

def serialize_meta(meta): 
    #serialize in json 
    meta_serialized = json.dumps({
    'driver': meta['driver'],
    'dtype': meta['dtype'],
    'nodata': meta['nodata'],
    'width': meta['width'],
    'height': meta['height'],
    'count': meta['count'],
    'crs': str(meta['crs']),  # Convert the CRS object to a string
    'transform': str(meta['transform'])  # Convert the Affine object to a string
    })

    return meta_serialized

def create_hdf5_from_data(sentinel_data, hdf5_filename='hypercube.h5'):
    with h5py.File(hdf5_filename, 'w') as hdf_file:

        #Retrieve meta
        meta = get_meta()

        # Save altitude data
        altitude_data =  get_altitude_data(meta) 
        hdf_file.create_dataset('altitude', data=altitude_data, compression='gzip', compression_opts=9)

        # Save combined mask data
        mask = get_mask(meta)
        hdf_file.create_dataset('mask', data=mask.astype(bool), compression='gzip', compression_opts=9)

        # Save data for each month
        for year in sentinel_data.keys():
            for month in sentinel_data[year].keys():
                dataset_name = f"{month}"               
                hdf_file.create_dataset(dataset_name, data=sentinel_data[year][month], compression='gzip', compression_opts=9)

            print(1,"/12")
        # Save metadata
        meta_serialized = serialize_meta(meta)
        hdf_file.attrs['meta'] = meta_serialized

# Retrieve data using get_data function
sentinel_data = get_data()

# Create HDF5 file using the retrieved data
create_hdf5_from_data(sentinel_data)