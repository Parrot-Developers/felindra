#  Copyright (C) 2022 Parrot Drones SAS
#
#  Redistribution and use in source and binary forms, with or without
#  modification, are permitted provided that the following conditions
#  are met:
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in
#    the documentation and/or other materials provided with the
#    distribution.
#  * Neither the name of the Parrot Company nor the names
#    of its contributors may be used to endorse or promote products
#    derived from this software without specific prior written
#    permission.
#
#  THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
#  "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
#  LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
#  FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
#  PARROT COMPANY BE LIABLE FOR ANY DIRECT, INDIRECT,
#  INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
#  BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS
#  OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED
#  AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
#  OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT
#  OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
#  SUCH DAMAGE.


import logging
import math
import os
import sys
from typing import Optional

from . import constants as C


LOGGER = logging.getLogger(__name__)


def setup_log(colors: bool = False, verbose: bool = False) -> None:
    """
    Setup logging in a Alchemy-like format.

    Parameters:
        colors (bool): Use colored logs.
        verbose (bool): Show debug-level logs.
    """
    # Return color 'clr' or empty depending on 'colors' option
    def getclr(clr):
        return clr if colors else ""

    # Setup basic log, with custom format and default level depending on verbose
    logging.basicConfig(
        level=(logging.DEBUG if verbose else logging.INFO),
        format="%(levelname)s %(message)s" + getclr(C.CLR_DEFAULT),
        stream=sys.stderr,
    )
    logging.addLevelName(logging.CRITICAL, getclr(C.CLR_RED) + "[C]")
    logging.addLevelName(logging.ERROR, getclr(C.CLR_RED) + "[E]")
    logging.addLevelName(logging.WARNING, getclr(C.CLR_YELLOW) + "[W]")
    logging.addLevelName(logging.INFO, getclr(C.CLR_GREEN) + "[I]")
    logging.addLevelName(logging.DEBUG, "[D]")


def index_to_str(index: int, max_val: int) -> str:
    """
    Return a number with leading zeroes depending on the max value.

    Parameters:
        index (int): the index to format
        max_val (int): the maximum number of values
    Return
        (str): the formatted index.
    """
    if max_val < 0 or index < 0:
        return ""
    idx_size = int(math.log10(max_val or 1)) + 1
    return f"{index:0{idx_size}d}"


def locate_share_dir() -> str:
    """
    Locate the share directory of the package.

    Returns:
        (str): the package share directory of None if not found
    """
    if "SYSROOT" in os.environ:
        # native-wrapper case
        return os.path.join(os.environ["SYSROOT"], "usr", "share", "felindra")
    # python wheel case
    return os.path.join(os.path.abspath(os.path.dirname(__file__)), "etc", "share")


def is_media_supported(file_path: str) -> bool:
    """
    Check if a media file path is supported.

    Parameters:
        file_path (str): the media file path to be checked
    Returns:
        (bool): whether the meda file path is supported
    """
    for ext in [".JPG", ".DNG"]:
        if file_path.endswith(ext):
            return True
    return False


def media_file_to_sig(media_file: str) -> Optional[str]:
    """
    Convert a media file path to its signature file name by replacing its extension.

    Parameters:
        media_file (str): the media file path to convert
    Returns:
        (str): the signature file path or None if not found
    """
    ext = os.path.splitext(media_file)[1]
    sig_match_table = [[".JPG", ".SIG"], [".DNG", ".DIG"]]
    for candidate in sig_match_table:
        if ext.upper() == candidate[0].upper():
            return media_file.replace(ext, candidate[1])
    return None


def format_output(data_file: str, status: int, log: str) -> None:
    """
    Format a list output using the log level as result.

    Parameters:
        data_file (str): input file path
        status (logging.ERROR|WARNING|INFO): the log level
        log: the log message to display with the input file name
    """
    if status == logging.ERROR:
        prefix = "✕"
        clr = C.CLR_RED
    if status == logging.WARNING:
        prefix = "~"
        clr = C.CLR_YELLOW
    if status == logging.INFO:
        prefix = "✓"
        clr = C.CLR_GREEN
    print(f"{clr} {prefix} {os.path.basename(data_file)}: {log}{C.CLR_DEFAULT}")
