import sys
from pathlib import Path

import matplotlib.pyplot as plt
import nibabel as nib
import numpy as np
import tifffile as tiff

parent_dir = Path(__file__).resolve().parent.parent
if str(parent_dir) not in sys.path:
    sys.path.append(str(parent_dir))

from utils.io_helpers import (
    load_script_config,
    normalize_user_path,
    require_absolute_path,
    require_dir,
)


# -------------------------
# CONFIG LOADING
# -------------------------
script_path = Path(__file__).resolve()
test_mode = False
cfg = load_script_config(script_path, "volumetric_heatmap", test_mode=test_mode)

# -------------------------
# CONFIG PARAMETERS
# -------------------------
directory_path = require_dir(
    require_absolute_path(normalize_user_path(cfg["directory_path"]), "Input TIFF directory"),
    "Input TIFF directory",
)
filename_suffix = cfg["filename_suffix"]
plot_cmap = cfg["plot_cmap"]
output_nifti_name = cfg["output_nifti_name"]

# -------------------------
# MAIN
# -------------------------
image_paths = sorted(p for p in directory_path.iterdir() if p.name.endswith(filename_suffix))
if not image_paths:
    raise RuntimeError(f"No TIFF files ending with '{filename_suffix}' found in:\n{directory_path}")

image_data_list = [tiff.imread(path) for path in image_paths]
stacked_data = np.stack(image_data_list, axis=0)
average_volume = np.mean(stacked_data, axis=0)

if average_volume.ndim < 3:
    raise RuntimeError(f"Expected at least 3D image data, got shape: {average_volume.shape}")

middle_slice_index = average_volume.shape[0] // 2
slice_data = average_volume[middle_slice_index, :, :]

plt.figure(figsize=(8, 6))
plt.imshow(slice_data, cmap=plot_cmap)
plt.colorbar(label="Intensity")
plt.title(f"Average Slice at index {middle_slice_index} with {plot_cmap} colormap")
plt.axis("off")
plt.show()

nifti_file_path = directory_path / output_nifti_name
nifti_image = nib.Nifti1Image(average_volume, affine=np.eye(4))
nib.save(nifti_image, nifti_file_path)
