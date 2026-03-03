import os
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import nibabel as nib
import numpy as np
import tifffile as tiff

parent_dir = Path(__file__).resolve().parent.parent
if str(parent_dir) not in sys.path:
    sys.path.append(str(parent_dir))

from utils.io_helpers import load_script_config, normalize_user_path


def resolve_config_path(path_like: str | Path, script_dir: Path) -> Path:
    p = normalize_user_path(path_like)
    return p if p.is_absolute() else (script_dir / p).resolve()


script_path = Path(__file__).resolve()
script_dir = script_path.parent
test_mode = False
cfg = load_script_config(script_path, "volumetric_heatmap", test_mode=test_mode)

directory_path = resolve_config_path(cfg["directory_path"], script_dir)
filename_suffix = cfg.get("filename_suffix", "_cell_locations_ref_space.tif")
slice_index = int(cfg.get("slice_index", 400))
plot_cmap = cfg.get("plot_cmap", "magma")
output_nifti_name = cfg.get("output_nifti_name", "average_volume.nii.gz")

image_data_list = []
for filename in os.listdir(directory_path):
    if filename.endswith(filename_suffix):
        file_path = os.path.join(directory_path, filename)
        image_data = tiff.imread(file_path)
        image_data_list.append(image_data)

if not image_data_list:
    raise RuntimeError(f"No TIFF files ending with '{filename_suffix}' found in: {directory_path}")

stacked_data = np.stack(image_data_list, axis=0)
average_volume = np.mean(stacked_data, axis=0)

middle_slice_index = average_volume.shape[0] // 2
slice_data = average_volume[:, :, slice_index]

plt.figure(figsize=(8, 6))
plt.imshow(slice_data, cmap=plot_cmap)
plt.colorbar(label="Intensity")
plt.title(f"Average Slice at Z={middle_slice_index} with {plot_cmap} colormap")
plt.axis("off")
plt.show()

nifti_file_path = os.path.join(directory_path, output_nifti_name)
nifti_image = nib.Nifti1Image(average_volume, affine=np.eye(4))
nib.save(nifti_image, nifti_file_path)
