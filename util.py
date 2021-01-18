from typing import Tuple, List
import subprocess
import datetime
from recordtype import recordtype

# Movie type (essentially a mutable namedtuple)
Movie = recordtype("Movie", "fname height width create_date rotation")


def run_cmd(cmd: str, **kwargs) -> subprocess.CompletedProcess:
    """
    Simple wrapper around subprocess run
    """
    return subprocess.run(cmd, shell=True, check=True, **kwargs)


def parse_datetime_with_tz(exif_date: str) -> datetime.datetime:
    """
    Parses the date/time captured from the exif data, assuming timezone is already incorporated
    """
    date, tod = (exif_date.split(" "))
    tod = tod.split("-")[0]
    yr, mo, day = date.split(":")
    hour, minute, sec = tod.split(":")
    try:
        d = datetime.date(int(yr), int(mo), int(day))
        t = datetime.time(int(hour), int(minute), int(sec))
    except ValueError:
        print("Invalid date/time information")
        return None
    return datetime.datetime.combine(d, t)


def get_date_info(exif_data: dict,
                  timestamp_keys: List[str]) -> datetime.datetime:
    """
    Parses the exif data from each video looking for the creation date/time keys
    """

    # Look for the creation date/time keys in the metadata
    timestamp_val = None
    timestamp_key = None
    i = 0
    while timestamp_val is None and i < len(timestamp_keys):
        timestamp_key = timestamp_keys[i]
        timestamp_val = exif_data.get(timestamp_key)
        i += 1

    # If/else statements disambiguating how to parse each case
    date_info = None
    if timestamp_key in [
            "QuickTime:DateTimeOriginal", "QuickTime:CreationDate"
    ]:
        # In this class of tags, the timezone data is incorporated into the date already but also attached to the end of the date string
        date_info = parse_datetime_with_tz(timestamp_val)
    elif timestamp_key in ["QuickTime:CreateDate"]:
        # This class of tags has an additional tag to reference for the timezone. We can use the same function to get the UTC datetime
        date_info = parse_datetime_with_tz(timestamp_val)

        # If there"s a time zone, adjust accordingly
        if "QuickTime:TimeZone" in exif_data:
            tz_offset = exif_data["QuickTime:TimeZone"]
            date_info += datetime.timedelta(minutes=tz_offset)

    # Returns date information (or None if not date info found)
    return date_info


def create_concat_cmd(movies: List[Movie],
                      out_fname: str,
                      max_dims: Tuple[int, int] = (1920, 1080),
                      overlay_clock: bool = True,
                      verbosity: str = "quiet") -> str:
    cmd = "ffmpeg \\\n"
    cmd += "    -y \\\n"
    cmd += f"    -loglevel {verbosity} \\\n"
    cmd += "    -stats \\\n"

    n = len(movies)
    for mov in movies:
        cmd += f"    -i {mov.fname} \\\n"

    # Create the string that pulls the relevant streams from the inputs. Assumes all inputs have 1 audio and 1 video stream
    complex_filter_str = "\""
    for i, mov in enumerate(movies):
        filter_str = create_filter_str(mov, max_dims, overlay_clock)
        complex_filter_str += f"[{i}:v]{filter_str}[v{i}]; \\\n"

    for i, mov in enumerate(movies):
        complex_filter_str += f"[v{i}]"
        complex_filter_str += f"[{i}:a]"

    # Finish the command string with the number of streams to join (n) and declare that there will always be 1 audio and 1 video output stream
    complex_filter_str += f"concat=n={n}:v=1:a=1[v][a]\""

    cmd += f"    -filter_complex \\\n{complex_filter_str} \\\n"

    # Map the concatenated streams to the output file
    cmd += "    -map \"[v]\" \\\n"
    cmd += "    -map \"[a]\" \\\n"
    cmd += "    -vcodec libx264 \\\n"
    cmd += "    -acodec aac \\\n"

    # Add the output file
    cmd += f"    {out_fname}"

    return cmd


def swap_dims(movie: Movie) -> None:
    """
    Simply swaps the height and width attributes for a movie. Called with rotation is not 0.
    """
    tmp = movie.width
    movie.width = movie.height
    movie.height = tmp


def create_filter_str(movie: Movie,
                      max_dims: Tuple[int, int],
                      overlay_clock: bool = True) -> str:
    # Open filter string
    filter_str = "setpts=PTS-STARTPTS, "

    # Match dimensions to rotated content
    if movie.rotation != 0:
        if movie.rotation == 90:
            swap_dims(movie)
            movie.rotation = 0
        elif movie.rotation == 270:
            swap_dims(movie)
            movie.rotation = 0

    # Scale to the max dims (assume the input images are no worse than 1280 x 720). Warn if video dimensions below that.
    if ((movie.width > movie.height) and
        ((movie.width < 1280) or
         (movie.height < 720))) or ((movie.width <= movie.height) and
                                    ((movie.height < 1280) or
                                     (movie.width < 720))):
        print(
            f"`{movie.fname}` is less than (1280x720) resolution. Results may look pixelated."
        )

    # Do nothing when:
    # * both dimensions are correct
    # * one dimension is correct and the other is smaller
    scale = False
    # Case 1: Downscale height, adjust width accordingly (will pad)
    if (movie.width < max_dims[0]) and (movie.height > max_dims[1]):
        height_ratio = movie.height / max_dims[1]
        movie.height = max_dims[1]
        movie.width = int(movie.width / height_ratio)
        scale = True
    # Case 2: Downscale width, adjust height accordingly (will pad)
    elif (movie.width > max_dims[0]) and (movie.height < max_dims[1]):
        width_ratio = movie.width / max_dims[0]
        movie.width = max_dims[0]
        movie.height = int(movie.height / width_ratio)
        scale = True
    # Case 3: Upscale
    elif (movie.width < max_dims[0]) and (movie.height < max_dims[1]):
        width_ratio = movie.width / max_dims[0]
        height_ratio = movie.height / max_dims[1]
        # Upscale based on width
        if width_ratio >= height_ratio:
            movie.width = max_dims[0]
            movie.height = int(movie.height / width_ratio)
            scale = True
        # Upscale based on height
        else:
            movie.height = max_dims[1]
            movie.width = int(movie.width / height_ratio)
            scale = True
    # Case 4: Downscale
    elif (movie.width > max_dims[0]) and (movie.height > max_dims[1]):
        width_ratio = movie.width / max_dims[0]
        height_ratio = movie.height / max_dims[1]
        # Downscale based on width
        if width_ratio >= height_ratio:
            movie.width = max_dims[0]
            movie.height = int(movie.height / width_ratio)
            scale = True
        # Downscale based on height
        else:
            movie.height = max_dims[1]
            movie.width = int(movie.width / height_ratio)
            scale = True

    # Add the rescale filter
    if scale:
        filter_str += f"scale={movie.width}:{movie.height}, "

    # Pad the videos to make them all same size
    if (movie.width < max_dims[0]) or (movie.height < max_dims[1]):
        filter_str += f"pad=width={max_dims[0]}:height={max_dims[1]}:x={(max_dims[0] - movie.width) // 2}:y={(max_dims[1] - movie.height) // 2}:color=black, "

    filter_str += "setsar=1"

    # Overlay the clock
    if movie.create_date is not None and overlay_clock:
        filter_str += f", drawtext=expansion=strftime: basetime=$(date +%s -d\'{movie.create_date.date()} {movie.create_date.time()}\')000000 : fontcolor=white : text=\'%^b %d, %Y%n%l\\\\:%M%p\' : fontsize=36 : y={movie.height}-4*lh : x={movie.width + (max_dims[0] - movie.width) // 2}-text_w-2*max_glyph_w"

    return filter_str


def duplicate_check(movies: List[Movie]) -> None:
    """
    Warns user of possible duplicate clips when multiple clips have the same exact timestamp (to the tenth of a second).
    """
    unique_time = {}
    for m in movies:
        if m.create_date.timestamp() not in unique_time:
            unique_time[m.create_date.timestamp()] = m
        else:
            print(
                f"ALERT: Possible duplicate video found: {m.fname} and {unique_time[m.create_date.timestamp()].fname} share the same timestamp!"
            )


def check_audio(movies: List[Movie]) -> None:
    """
    Calls ffprobe on each clip to confirm that there is an audio stream. If one doesn't exist, alerts the user.
    """
    for m in movies:
        output = run_cmd(
            f"ffprobe -i {m.fname} -show_streams -select_streams a -loglevel error",
            capture_output=True)
        if not output.stdout:
            print(
                f"ALERT: Video missing audio stream! Merging will fail! ({m.fname})"
            )