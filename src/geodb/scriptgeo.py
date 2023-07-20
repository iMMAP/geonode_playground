import geopandas as gpd

shapefile_path = "~/Documents/temp_extracted_files/mi.shp"

data = gpd.read_file(shapefile_path)

print(data)