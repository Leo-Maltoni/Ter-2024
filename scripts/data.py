import geopandas as gpd
import rasterio
from rasterio.mask import geometry_mask
import numpy as np
import scipy.io
from rasterio.warp import calculate_default_transform, reproject, Resampling
from scripts.paths import get_elevation_data_path, get_geojson_path, get_sentinel_data_path

def calculate_ndvi(red, nir):
    # NDVI calculation: (NIR - Red) / (NIR + Red)
    ndvi = (nir - red) / (nir + red)
    ndvi[np.isinf(ndvi)] = np.nan
    return ndvi

def get_mask(meta):
    gdf = gpd.read_file(get_geojson_path())
    gdf = gdf.to_crs(meta['crs'])
    shape = meta['height'], meta['width']
    transform = meta['transform']

    labels = ["Limite", "Assez_limite", "Moyen", "Assez_fort", "Fort_a_tres_fort"]
    mask = np.zeros((shape), dtype=bool)
    for label in labels:
        label_mask = geometry_mask(gdf[gdf["pot_global"] == label].geometry, 
                            out_shape=shape, 
                            transform=transform, 
                            invert=True)
        mask |= label_mask
    return mask 

def get_data(load_saved=False):
    if load_saved:
        print("lik")
        return scipy.io.loadmat('./data/data.mat')['data'].keys()
    print("hhh")
    sentinel_data_path = get_sentinel_data_path()
    years = map(str, list(sentinel_data_path.keys()))
    meta = None 
    mask = None 
    sentinel_data = {}
    for year in years:
        sentinel_data[year] = {}
        months = map(str, sorted(list(sentinel_data_path[int(year)].keys())))
        for month in months:
            bands = sentinel_data_path[int(year)][int(month)]
            blue = rasterio.open(bands["B02"]).read(1).astype(np.float32)
            green = rasterio.open(bands["B03"]).read(1).astype(np.float32)
            red = rasterio.open(bands["B04"]).read(1).astype(np.float32)
            if meta == None:
                nir = rasterio.open(bands["B08"])
                meta = nir.meta  # They all have the same meta
                nir = nir.read(1).astype(np.float32)
            else:
                nir = rasterio.open(bands["B08"]).read(1).astype(np.float32)
        
            if mask is None:
                mask = get_mask(meta) 

            blue[~mask] = np.nan
            green[~mask] = np.nan
            red[~mask] = np.nan
            nir[~mask] = np.nan
            
            # Calculate NDVI
            ndvi = (nir - red) / (nir + red)
            ndvi[~mask] = np.nan
            
            # Stack bands into a 3D array
            month_data = np.stack([blue, green, red, nir, ndvi], axis=-1)
            sentinel_data[year][month] = month_data  # Store as 3D array
    
    scipy.io.savemat('./data/data.mat', {"data":sentinel_data})

    return sentinel_data

def get_altitude_data(meta):
    # Resample altitude data to match the other bands
    elevation_path = get_elevation_data_path()
    with rasterio.open(elevation_path) as src:
        altitude_meta = src.meta
        transform, width, height = calculate_default_transform(
            src.crs, meta['crs'], meta['width'], meta['height'], *src.bounds)
        altitude_resampled = np.zeros((meta['height'], meta['width']), np.float32)

        reproject(
            source=rasterio.band(src, 1),
            destination=altitude_resampled,
            src_transform=src.transform,
            src_crs=src.crs,
            dst_transform=meta['transform'],
            dst_crs=meta['crs'],
            resampling=Resampling.nearest)
        
        return altitude_resampled

def get_meta(): 
    meta = rasterio.open(get_sentinel_data_path()[2019][1]['B02']).meta

    return meta