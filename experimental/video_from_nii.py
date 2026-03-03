import cv2
import numpy as np
import nibabel as nib

# Specify paths and number of channels
file_path = r"M:\SmartSPIM_Data\2025\2025_11\2025_11_07\20251107_12_55_02_NB_100679_M_P14_C3_LAS_488Lectin_561NeuN_640Iba1_4x_4umstep_Destripe_DONE\\"
channels = 3

# Set the brightness adjustment factor. You can set separate ones for each channel.
brightness_factor_list = [1,1,1]  # Increase for brighter, decrease below 1.0 for darker



# Loop through volumes and create videos
for i in range(channels):
    brightness_factor = brightness_factor_list[i]
    nii_file = rf"{file_path}ch{i}_iso20um.nii.gz"
    nii_img = nib.load(nii_file)
    data = nii_img.get_fdata()
    # change the order of the axes
    data = np.transpose(data, (2, 0, 1))
    # flip two of the axes
    data = data[:, ::-1, ::-1]
    nii_data = data.copy()
    # Normalize the data and clip the outlier frames
    min_val = np.percentile(nii_data, 1)
    max_val = np.percentile(nii_data, 99.9)
    nii_data = np.clip(nii_data, min_val, max_val)
    nii_data = (nii_data - min_val) / (max_val - min_val) * 255
    nii_data = nii_data.astype(np.uint16)

    # Determine the maximum resolution needed across all planes
    output_res = (max(*nii_data.shape), max(*nii_data.shape))

    # Define the number of frames per second for the output video
    fps = 30

    output_file = nii_file.split(".")[0] + "_video.mp4"

    # Create a VideoWriter object using the maximum resolution
    fourcc = cv2.VideoWriter_fourcc(*"MP4V")
    out = cv2.VideoWriter(output_file, fourcc, fps, output_res)

    # Create a loop to iterate through each plane
    for plane in range(3):
        # Determine the range of slice indices
        if plane == 2:
            indices = range(nii_data.shape[plane] - 1, -1, -1)  # Reverse order for the third plane
        else:
            indices = range(nii_data.shape[plane])

        # Create a loop to iterate through each slice in the plane
        for slice_idx in indices:
            # Extract the 2D image data
            if plane == 0:
                img_data = np.rot90(nii_data[slice_idx, :, :])  # Keep 90 degrees counterclockwise
            elif plane == 1:
                img_data = nii_data[:, slice_idx, :]  # Rotate 90 degrees clockwise implicitly
            else:
                img_data = nii_data[:, :, slice_idx]  # Direct access for reversed order

            # Adjust brightness by scaling pixel values
            img_data = np.clip(img_data * brightness_factor, 0, 255).astype(np.uint8)

            # Calculate padding
            pad_vertical = (output_res[1] - img_data.shape[0]) // 2
            pad_horizontal = (output_res[0] - img_data.shape[1]) // 2

            # Equally pad around the img_data
            img_data_padded = np.pad(
                img_data,
                ((pad_vertical, output_res[1] - img_data.shape[0] - pad_vertical),
                (pad_horizontal, output_res[0] - img_data.shape[1] - pad_horizontal)),
                mode='constant',
                constant_values=0
            )

            # Write the image data to the output video file
            out.write(cv2.cvtColor(img_data_padded, cv2.COLOR_GRAY2BGR))

    # Release the VideoWriter object and close the output video file
    out.release()
