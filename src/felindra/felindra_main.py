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


import argparse
import logging
import os
import sys


from .libfelindra import verify_on_disk
from .libfelindra import verify_on_remote
from . import tools
from . import constants as C


LOGGER = logging.getLogger(__name__)


def on_subcommand_local(args):
    """
    Process 'local' subcommand.

    Parameters:
        args (Namespace): list of arguments from command line.
    """
    res_path = args.path
    sig_path = args.sig or None
    crt_path = args.cert
    skip = args.skip or False
    if not os.path.exists(res_path):
        LOGGER.error(f"Invalid resource path: '{res_path}'")
        return
    if not os.path.isfile(crt_path):
        LOGGER.error(f"Certificate file not found: '{crt_path}'")
        return
    return verify_on_disk(
        res_path=res_path, sig_path=sig_path, crt_path=crt_path, skip_unsigned=skip
    )


def on_subcommand_remote(args):
    """
    Process 'remote' subcommand.

    Parameters:
        args (Namespace): list of arguments from command line.
    """
    uid_filter = args.uid
    skip = args.skip or False
    ip_list = args.ip or [C.ADB_DEFAULT_IP_RNDIS, C.ADB_DEFAULT_IP_WIFI]
    return verify_on_remote(ip_list=ip_list, uid_filter=uid_filter, skip_unsigned=skip)


def print_welcome():
    """
    Print welcome.
    """
    print(r"Felindra")
    print(r"Copyright (c) 2021 Parrot Drones SAS")
    print()


def main():
    """
    Entry point.
    """
    tools.setup_log(colors=True)

    print_welcome()

    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbose", action="store_true", help="be more verbose in logs")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    subparsers.required = True

    # create the parser for the 'remote' command
    parser_l = subparsers.add_parser("remote", help="run felindra remote", aliases=["l", "loc"])
    parser_l.add_argument("uid", nargs="?", help="filter with a media or resource UID")
    parser_l.add_argument(
        "-i",
        "--ip",
        nargs="+",
        help="specify the drone IP address (if not set, try RNDIS first then Wi-Fi)",
    )
    parser_l.add_argument(
        "-S", "--skip", action="store_true", help="skip media that do not have signatures"
    )
    parser_l.set_defaults(func=on_subcommand_remote)

    # create the parser for the 'local' command
    parser_r = subparsers.add_parser("local", help="run felindra on local", aliases=["r", "rem"])
    parser_r.add_argument("path", help="input file or dir to verify")
    parser_r.add_argument("-s", "--sig", help="signature file (default is .SIG|.DIG)")
    parser_r.add_argument("cert", help="drone certificate")
    parser_r.add_argument(
        "-S", "--skip", action="store_true", help="skip media that do not have signatures"
    )
    parser_r.set_defaults(func=on_subcommand_local)

    args = parser.parse_args()

    verbose = args.verbose or False
    if verbose:
        LOGGER.setLevel(logging.DEBUG)
        logging.getLogger("felindra").setLevel(logging.DEBUG)

    args.func(args)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print()
        LOGGER.error("Interrupted")
        sys.exit(1)
