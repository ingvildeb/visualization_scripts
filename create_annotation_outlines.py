import nibabel as nib
from glob import glob
import numpy as np
from scipy.ndimage import binary_erosion
from tqdm import tqdm

anno_path = r"Z:\Labmembers\Ingvild\Testing_CellPose\test_data\ANTs_TransformedImage.nii.gz"

img = nib.load(anno_path)
arr = img.get_fdata()
# Create an empty array to store edges
edges = np.zeros_like(arr)
# Detect edges by comparing the original array with its eroded version
for label in tqdm(np.unique(arr)):
    if label == 0:
        continue  # Skip background
    region = arr == label
    eroded_region = binary_erosion(region)
    edges += region & ~eroded_region
# Save the edges volume as a new NIfTI image
edges_img = nib.Nifti1Image(edges.astype(np.uint8), img.affine)
nib.save(edges_img, f"{anno_path}_edges_volume.nii")
