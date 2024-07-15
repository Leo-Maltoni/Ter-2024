import rasterio
import numpy as np
from matplotlib import pyplot as plt
import json
from shapely.geometry import shape, Point
from shapely.strtree import STRtree

# Function to read a GeoTIFF file and return the elevation data as a numpy array and metadata
def read_geotiff_to_array(filepath):
    with rasterio.open(filepath) as src:
        elevation_array = src.read(1)
        crs = src.crs
        width = src.width
        height = src.height
    return elevation_array, crs, width, height

# Calculate spatial coordinates for each pixel using provided bounds
def calculate_spatial_coordinates(west, east, south, north, width, height):
    lon = np.linspace(west, east, width)
    lat = np.linspace(north, south, height)  # Note: Latitude should decrease from north to south
    lon_grid, lat_grid = np.meshgrid(lon, lat)
    return lon_grid, lat_grid

# Path to your GeoTIFF file
geotiff_path = 'raw_elevation_data_10m.tif'

# Read the GeoTIFF file and store the elevation values in a numpy array
elevation_data, crs, width, height = read_geotiff_to_array(geotiff_path)

# Define the spatial bounds
west_bound = 2.999749474120944
east_bound = 4.374940058749246
south_bound = 43.256794294201605
north_bound = 44.25341758107761

# Calculate spatial coordinates for each pixel
lon_grid, lat_grid = calculate_spatial_coordinates(west_bound, east_bound, south_bound, north_bound, width, height)

# Flatten the coordinate grids to create points
points = np.column_stack((lon_grid.ravel(), lat_grid.ravel()))

# Load GeoJSON file containing sectors
with open('bd-sol-gdpa-herault@data-herault-occitanie.geojson') as f:
    geojson_data = json.load(f)

# Create a list of polygons from the GeoJSON file, filtering out features with None geometry
polygons = [shape(feature['geometry']) for feature in geojson_data['features'] if feature['geometry'] is not None]

# Build a spatial index for the polygons
spatial_index = STRtree(polygons)
# Function to check if points are within any polygons
def points_within_polygons(points, polygons, spatial_index):
    mask = np.zeros(points.shape[0], dtype=bool)
    for i, point in enumerate(points):
        if i % 100_000 == 0:  # Only check a fraction of the points for debugging
            print(f"Checking point {i}/{len(points)}: {point}")
        shapely_point = Point(point)
        for polygon in polygons:
            if polygon.contains(shapely_point):
                print(shapely_point)
                mask[i] = True
    return mask

# Check which points are within the polygons, limiting the number of points checked for debugging
fraction_to_check = len(points) // 10  # Check only 10% of the points for debugging
mask = points_within_polygons(points[:fraction_to_check], polygons, spatial_index)

# Reshape the mask to the shape of the elevation data
# Note: Adjusting the shape to only the fraction we checked
mask = mask.reshape(lon_grid[:fraction_to_check].shape)

# Apply the mask to the elevation data to keep only the points that match the polygons
masked_elevation_data = np.where(mask, elevation_data[:mask.shape[0], :mask.shape[1]], np.nan)

# Save the masked elevation data to a new GeoTIFF file
output_path = 'masked_elevation_data_debug.tif'
with rasterio.open(
    output_path,
    'w',
    driver='GTiff',
    height=masked_elevation_data.shape[0],
    width=masked_elevation_data.shape[1],
    count=1,
    dtype=masked_elevation_data.dtype,
    crs=crs,  # Ensure CRS is correctly passed
    transform=rasterio.transform.from_bounds(west_bound, south_bound, east_bound, north_bound, width, height),
) as dst:
    dst.write(masked_elevation_data, 1)

# Display the remaining pixels with matplotlib
plt.figure(figsize=(10, 10))
plt.imshow(masked_elevation_data, cmap='terrain', extent=[west_bound, east_bound, south_bound, north_bound])
plt.colorbar(label='Elevation (m)')
plt.xlabel('Longitude')
plt.ylabel('Latitude')
plt.title('Elevation Data within Polygons (Debug Fraction)')
plt.show()
