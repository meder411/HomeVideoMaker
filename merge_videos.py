"""
Author: Marc Eder
Description: A tool to merge captured video clips into longer home movies with camcorder-style data/time overlays
"""

import os.path as osp
import argparse
import glob
import exiftool
from util import *

# Currently accepts these types
supported_input_types = (".mp4", ".mov", ".avi")

# Keys to try in the EXIF data in order of precedence
timestamp_keys = [
    "QuickTime:DateTimeOriginal", "QuickTime:CreationDate",
    "QuickTime:CreateDate"
]


def parse_arguments() -> argparse.Namespace:
    """
    Create and parse the command line arguments
    """
    # Create arguments
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input-dir",
        "-i",
        type=str,
        required=True,
        help="Path to directory containing clips to merge",
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        type=str,
        required=True,
        help="Where the output video is stored",
    )
    parser.add_argument(
        "--num-parts",
        "-n",
        type=int,
        default=1,
        help="Number of movies to merge these clips into",
    )
    parser.add_argument("--no-date",
                        action="store_false",
                        default=True,
                        help="Disables date overlay")
    parser.add_argument(
        "--verbosity",
        "-v",
        type=str,
        default="quiet",
        help="ffmpeg verbosity level",
    )
    parser.add_argument("--debug-cmd",
                        action="store_true",
                        default=False,
                        help="Prints ffmpeg command")

    # Parse arguments
    args = parser.parse_args()

    # Return namespace wrapper of arguments
    return args


def main(args) -> None:
    """
    Main operation
    """

    # Parse the arguments
    # Output filename is the input directory name
    out_fname = osp.join(args.output_dir,
                         osp.basename(args.input_dir.rstrip("/")) + ".mp4")
    debug = args.debug_cmd  # Whether to print the ffmpeg command
    num_parts = args.num_parts  # Number of movies to merge clips into
    overlay_clock = args.no_date  # Whether to overlay the clock on the image
    verbosity = args.verbosity  # FFMPEG verbosity level

    # Get all files in the provided directory
    files = glob.glob(osp.join(args.input_dir, "*"))

    # Cull the files only to supported inputs
    clips = []
    for file in files:
        ext = osp.splitext(file)[1]
        if not ext.lower() in supported_input_types:
            print(
                f"`{osp.splitext(file)[1]}` file format not supported. `{file}` will be skipped!"
            )
        else:
            clips.append(file)

    # Obtain the exif data for each video
    movies = []
    with exiftool.ExifTool() as exif:
        for vid in clips:
            # Get all the metadata
            exif_data = exif.get_metadata(vid)

            # Extract date info from the metadata
            date_info = get_date_info(exif_data)

            if date_info is None:
                # If none of the keys are found, warn but add the video anyway
                print(
                    f"Failed to find creation timestamp key in EXIF data for video `{vid}`! No timestamp will be added and clip may be sorted out of order."
                )

            # Create a Movie recordtype and add it to the list
            movies.append(
                Movie(fname=vid,
                      height=exif_data["QuickTime:ImageHeight"],
                      width=exif_data["QuickTime:ImageWidth"],
                      create_date=date_info,
                      rotation=exif_data["Composite:Rotation"]))

    # Sort by creation date, ascending
    movies.sort(key=lambda x: x.create_date)

    # Check for any duplicate timestamps, which may indicate redundant clips
    print("Checking for potential duplicate clips...........")
    duplicate_check(movies)
    print("Done!")

    # Check all clips have audio streams
    print("\n\nChecking that all clips have audio streams.........")
    check_audio(movies)
    print("Done!")

    # Confirm user wants to continue
    user_in = ""
    while user_in != "yes":
        user_in = input("Do you want to continue merging (yes/no)?: ")

        if user_in == "no":
            print("Exiting!")
            exit()

    # Split movies based on number of parts desired
    if num_parts > 1:

        # How many clips to put in each merged movie
        step = len(movies) // num_parts

        # For each movie to create
        for i in range(num_parts):
            # Grab a subset of the temporally ordered movies
            start = i * step
            end = (i + 1) * step if i < num_parts - 1 else len(movies)
            movies_subset = movies[start:end]

            # Add numerical index to output files
            filename, ext = osp.splitext(out_fname)
            indexed_out_fname = f"{filename}{i}{ext}"

            # Build the concatenation command by parsing the movie info
            concat_cmd = create_concat_cmd(movies_subset, indexed_out_fname,
                                           overlay_clock, args.verbosity)
            if args.debug_cmd:
                print(concat_cmd)
            run_cmd(concat_cmd)

    else:
        # Build the concatenation command by parsing the movie info
        concat_cmd = create_concat_cmd(movies, out_fname, overlay_clock,
                                       args.verbosity)
        if args.debug_cmd:
            print(concat_cmd)
        run_cmd(concat_cmd)


# =========================================================================== #
# ================================== MAIN =================================== #
# =========================================================================== #

if __name__ == '__main__':
    args = parse_args()
    main(args)