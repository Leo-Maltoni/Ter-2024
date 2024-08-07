import geopandas as gpd
import rasterio
from rasterio.mask import geometry_mask
import numpy as np
import scipy.io

from scripts.paths import get_elevation_data_path, get_geojson_path, get_sentinel_data_path


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
        return scipy.io.loadmat('./data/data.mat')['data'].keys()
    
    sentinel_data_path = get_sentinel_data_path()
    years = map(str, list(sentinel_data_path.keys()))
    meta = None 
    mask = None 
    sentinel_data = {}
    for year in years:
        sentinel_data[year] = {}
        months = map(str, sorted(list(sentinel_data_path[int(year)].keys())))
        for month in months:
            sentinel_data[year][month] = {}
            bands = sentinel_data_path[int(year)][int(month)]
            blue = rasterio.open(bands["B02"]).read(1).astype(np.float32)
            green = rasterio.open(bands["B03"]).read(1).astype(np.float32)
            red = rasterio.open(bands["B04"]).read(1).astype(np.float32)
            if meta == None:
                nir = rasterio.open(bands["B08"])
                meta = nir.meta # They all have the same meta
                nir = nir.read(1).astype(np.float32)
            else:
                nir = rasterio.open(bands["B08"]).read(1).astype(np.float32)
        
            if mask == None:
                mask = get_mask(meta) 

            blue[~mask] = np.nan
            green[~mask] = np.nan
            red[~mask] = np.nan
            nir[~mask] = np.nan
            
            sentinel_data[year][month]["B02"] = blue
            sentinel_data[year][month]["B03"] = green
            sentinel_data[year][month]["B04"] = red
            sentinel_data[year][month]["B08"] = nir 

            break
    
    scipy.io.savemat('./data/data.mat', {"data":sentinel_data})

    return sentinel_data