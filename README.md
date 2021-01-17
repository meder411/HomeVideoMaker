# Home Video Maker

A simple python utility that wraps the [`exiftool`](https://github.com/smarnach/pyexiftool) package and [`ffmpeg`](https://ffmpeg.org/) to concatenate movies clips into a single movie. Given a folder of clips, this tool automatically sorts the clips based on creation date, super-imposes a timestamp on the bottom-right corners, and merges them into a single movie. 

The purpose is to turn the modern day collection of short smartphone clips into the classic camcorder-style home videos of the 1980's and 1990's.


## Dependencies

This code has been tested on Ubuntu 20.04 with Python 3.6+. Dependencies include:

 * `pyexiftool` (clone and install from [Github repo](https://github.com/smarnach/pyexiftool))
 * `ffmpeg` (tested with version 4.2.4)
 * `recordtype` (`pip install recordtype==1.3`)


## How to Use

After installing the above dependencies, you can call the command with:

```
python3 merge_videos.py -i INPUT_DIR -o OUTPUT_DIR [-n NUM_PARTS] [--no-date] [-v VERBOSITY] [--debug-cmd]
```

This will collect all video clips of supported types (".mp4", ".mov", ".avi"), sort them by creation date, and output a single, merged H.264 mp4 file to `<OUTPUT_DIR/<INPUT_DIR>.mp4`.

**Options**
 * `-i`/`--input-dir`: Path to the input directory containing all the clips to merge
 * `-o`/`--output-dir`: Path to the output directory where the merges movie(s) will be written
 * `-n`/`--num-parts`: (Optional) How many movies to merge the clips into (default: 1)
 * `--no-date`: (Optional) Include this flag to suppress the date overlay
 * `-v`/`--verbosity`: (Optional) [FFMPEG verbosity levels](https://superuser.com/a/438280) (default)
 * `--debug-cmd`: (Optional) Prints the constructed FFMPEG to console