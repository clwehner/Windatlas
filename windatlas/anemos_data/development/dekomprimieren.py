import os

if __name__ == "__main__":

    param = "rho"
    file_type = "/uba/anemos_winddata/20191029_anemosDataFull/UBA-Windatlas/TSNC-Format/"

    source_file = f"{file_type}{param}.10L.*"
    comp_folder = f"{file_type}compressed/"
    move_compressed = f"mv {source_file} {comp_folder}"
    os.system(move_compressed)

    for year in range(2009,2019,1):
        
        source_file = f"{file_type}compressed/{param}.10L.{year}.ts.nc"
        new_file = f"{file_type}{param}.10L.{year}.ts.nc"
        comand = f"nccopy -7 -d 0 {source_file} {new_file}"
        os.system(comand)
        chmod = f"chmod 755 {new_file}"
        os.system(chmod)