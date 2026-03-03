from pathlib import Path
import sys
import nibabel as nib
import numpy as np
import tifffile
from PIL import Image
import matplotlib.pyplot as plt
import cv2
import pandas as pd

parent_dir = Path(__file__).resolve().parent.parent
if str(parent_dir) not in sys.path:
    sys.path.append(str(parent_dir))

from utils.utils import prepare_hierarchy_info, atlas_to_svg, convert_colors, create_grayscale_mapping

# Give the input folder to your subject
input_folders = [Path(r"M:\SmartSPIM_Data\2025\2025_03\2025_03_20\20250320_17_02_13_NB_CS0290_M_P533_C57_LAS_488Lectin_561NeuN_640Iba1_4x_4umstep_Destripe_DONE\\"),
                 
                 ]

# Give the naming convention for your MIP folder
# This should be identical for all the subjects added to input_folder
mip_folder_name = "Ex_561_Ch1_stitched_MIP20um"

# Select a region of interest, the section will be selected to be in the middle of this regions'
# dorsoventral extent
roi = "Midbrain reticular nucleus"

# Choose style of your atlas plates
# Full image gives the atlas plate with all regions in their standard color scheme
# ROI image gives the atlas plate with only the ROI in color, and all other regions in grayscale
# You can set both to true if you want both options

full_image = False
roi_image = True


## MAIN CODE, do not edit

# Path setup
base_path = parent_dir
allen2intfile = base_path / "files" / "CCFv3_OntologyStructure_u16.xlsx"
hierarchy_file = base_path / "files" / "CCF_v3_ontology.json"
custom_hier_path = base_path / "files"

for input_folder in input_folders:
    subject_id = input_folder.stem.split("_")[5]
    atlas_path = input_folder / "_01_registration" / "ANTs_TransformedImage.nii.gz"
    mip_path = input_folder / mip_folder_name
    all_mips = list(mip_path.glob("*.tif"))

    # Prepare data
    allen2int = pd.read_excel(allen2intfile)
    color_mapping = dict(zip(allen2int['id_16bit'], allen2int['color_hex_triplet']))
    id_mapping, _, acronym_mapping, hierarchy_regions = prepare_hierarchy_info(hierarchy_file, custom_hier_path)


    # Get the ID of the user selected ROI
    roi_id = [key for key, value in id_mapping.items() if value == roi]

    # Check that the ROI exists
    if roi_id == []:
        print("No ID corresponding to the ROI name, check spelling")
    else:
        roi_id = roi_id[0]

    # Load the transformed atlas volume and read out the top and bottom slice coordinates for the ROI
    nifti_img = nib.load(atlas_path)
    data = np.asanyarray(nifti_img.dataobj)

    # Create the ROI mask
    roi_mask = (data == roi_id)

    # Get the indices (coordinates) where the ROI mask is True
    roi_indices = np.argwhere(roi_mask)

    if roi_indices.shape[0] == 0:
        print("No coordinates found for the specified ROI.")
    else:
        # Extract min and max coordinates
        min_coords = roi_indices.min(axis=0)
        max_coords = roi_indices.max(axis=0)

        top_coords = ((min_coords[0] + max_coords[0]) // 2, 
                    min_coords[1], 
                    (min_coords[2] + max_coords[2]) // 2)   # Top edge
        
        bottom_coords = ((min_coords[0] + max_coords[0]) // 2, 
                        max_coords[1], 
                        (min_coords[2] + max_coords[2]) // 2)  # Bottom edge

        top_plane = top_coords[1]
        bottom_plane = bottom_coords[1]
        middle_plane = int((top_plane + bottom_plane) / 2)
        middle_mip = all_mips[middle_plane]

        print(f"top plane is {top_plane}, bottom plane is {bottom_plane}, middle plane is {middle_plane}")
        print(f"middle mip is {middle_mip}")

        # Extract the atlas slice that is the middle of the ROI dorsoventral limits
        atlas_plate = data[:, middle_plane, :]
        
        # Load the raw MIP image and get its shape, for resizing the atlas plate
        image_data = np.array(Image.open(middle_mip))
        target_shape = image_data.shape[:2]

        # Rotate and scale the atlas image (where pixels have the atlas ids)
        # to the target shape
        rotated_atlas_image = np.rot90(atlas_plate)
        resized_atlas_image = cv2.resize(rotated_atlas_image, 
                                        (target_shape[1], target_shape[0]), 
                                        interpolation=cv2.INTER_NEAREST)
        if full_image == True:
            
            # Map ids in the atlas_image to rgb colors corresponding to Allen color codes
            color_image = convert_colors(atlas_plate, color_mapping)

            # Resize the color atlas image to the target size
            rotated_color_image = np.rot90(color_image)
            resized_color_image = cv2.resize(rotated_color_image, 
                                            (target_shape[1], target_shape[0]), 
                                            interpolation=cv2.INTER_NEAREST)
            
            # Prepare out path
            out_path = base_path / "images" / f"{subject_id}" / roi
            out_path.mkdir(parents=True, exist_ok=True)

            # Save tif version of the atlas plate
            file_name = f"{middle_mip.stem}_atlas_slice"
            tifffile.imwrite(out_path / f'{file_name}.tif', resized_color_image)
            
            # Save svg version of the atlas plate, made based on the atlas_image
            atlas_to_svg(resized_atlas_image, color_mapping, out_path / f'{file_name}.svg')

            # Show the colored image for verification
            plt.imshow(resized_color_image)
            plt.title("Full-Color Atlas Slice")
            plt.axis('off')
            plt.show()
                
        if roi_image:
           
            grayscale_mapping = create_grayscale_mapping(roi_id, atlas_plate, color_mapping)
            grayscale_image = convert_colors(atlas_plate, grayscale_mapping)

            # Resize the grayscale image to match target size
            rotated_gray_image = np.rot90(grayscale_image)
            resized_grayscale_image = cv2.resize(rotated_gray_image, 
                                                (target_shape[1], target_shape[0]), 
                                                interpolation=cv2.INTER_NEAREST)

            out_path = base_path / "images" / f"{subject_id}" / roi
            out_path.mkdir(parents=True, exist_ok=True)

            # Save the grayscale TIFF version with ROI color
            file_name_gray = f"{middle_mip.stem}_atlas_slice_roi"
            tifffile.imwrite(out_path / f'{file_name_gray}.tif', resized_grayscale_image)

            # Create SVG using the grayscale mapping with original color for the ROI
            grayscale_svg_filename = out_path / f'{file_name_gray}.svg'
    
            # Generate SVG using the updated color mapping
            atlas_to_svg(resized_atlas_image, grayscale_mapping, grayscale_svg_filename)

            # Show the grayscale image for verification
            plt.imshow(resized_grayscale_image)
            plt.title("Grayscale Atlas Slice with ROI")
            plt.axis('off')
            plt.show()

