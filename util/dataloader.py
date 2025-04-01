import numpy as np
from scipy.io import savemat

class DataLoader():
    def npy_to_csv(self,npy_path,csv_path):
        loaded_array = np.load(npy_path,allow_pickle=True)
        np.savetxt(csv_path, loaded_array, delimiter=',', fmt='%.4f')

    def npy_to_mat(self,npy_path,mat_path):
        data = np.load(npy_path)
        savemat(mat_path, {"data": data})

    def load_csv(self,csv_path,skip_header = 0):
        data = np.genfromtxt(csv_path, delimiter=',', skip_header=skip_header)
        return np.array(data)