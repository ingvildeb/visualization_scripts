# visualization scripts
 Scripts for visualizing brain-wide expression data mapped to the Allen CCF

 This repository contains various scripts for visualizing brain-wide expression data, e.g. numbers or densities of neurons. In principle, the scripts can be used to plot any metric across the brain, so long as the data is provided in the correct format. The scripts have been tested mainly with data mapped to CCFv3-2017, but may also work for data mapped to any version of the Allen CCF. 

 The repository is under development and any feedback is very welcome. I aim for this to be a useful resource for plotting brain-wide, atlas mapped data.

## Available plot types
All the plots can be made at different levels of the atlas hierarchy, or regions within a parent region can be selectively plotted. 
- Bar graphs (for single or multiple samples, and for one or more groups)
- Line graphs
- Heatmaps
- Brainglobe atlas heatmaps

## Other forms of visualization
- Create a flythrough video from a .nii file

## Format requirements:
It is essential that the data are formatted correctly for these scripts to work. See **files > counted_3d_cells.csv** for an example input file.
 - Data should be provided in Excel (.xlsx) format, with each region of the brain as a row and the data to be plotted in column(s).
 - The regions of the brain need to be identified by their atlas ID in a column named "ROI_id"
 - Every region in the Allen CCF should be present as a row, including higher-order regions. Thus, even if data were collected at the finest level of the hierarchy, pooled data from all children should be present for all parents.
 - If you want to plot data from different animals and groups, each subject should be represented in a separate sheet
 - The columns for the values to be plotted can be called anything (the user will specify the column name when using the different scripts), but should be named consistently across sheets for different animals in order to use scripts that group and average data

## Future plans:
- Support for plotting data mapped to the WHS rat brain atlas
- Automatic conversion of data generated via the QUINT workflow to the format required for these scripts
   
