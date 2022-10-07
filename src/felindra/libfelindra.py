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


from __future__ import annotations
import logging
import os
import tempfile
from typing import List, Any, Dict, Optional

from . import constants as C
from . import tools
from .webclient import WebClient
from .certificate import Certificate
from .resource import RemoteResource, LocalResource, Resource
from .resource import UnsignedResourceException


LOGGER = logging.getLogger(__name__)


def _get_resource_from_path(res_path: str, sig_path: str = None) -> Optional[Resource]:
    if not os.path.isfile(res_path):
        LOGGER.debug(f"Skipping {res_path}: not a regular file")
        return None
    if not tools.is_media_supported(res_path):
        LOGGER.debug(f"Skipping {res_path}: not a media file")
        return None
    if sig_path and not os.path.isfile(sig_path):
        LOGGER.warning(f"Signature file not found: '{sig_path}'. Searching for default pattern")
        sig_path = None
    if not sig_path:
        sig_path = tools.media_file_to_sig(res_path)
    return LocalResource(res_path, sig_path)


def _get_resource_list_from_path(
    res_path: str, sig_path=None, depth=0, max_depth=2
) -> Optional[List[Resource]]:
    media_list: List[Resource] = []
    if os.path.isdir(res_path):
        if sig_path:
            LOGGER.warning("Signature parameter cannot be used with directory. Ignoring it")
        # process dir
        for file in os.scandir(res_path):
            if file.is_dir() and depth < max_depth:
                res_list = _get_resource_list_from_path(file.path, None, depth + 1, max_depth)
                if res_list:
                    media_list.extend(res_list)
            elif file.is_file():
                new_res = _get_resource_from_path(file.path)
                if new_res:
                    media_list.append(new_res)
        return media_list
    if os.path.isfile(res_path):
        # return single resource object
        res = _get_resource_from_path(res_path, sig_path)
        return [res] if res else None
    return None


def _get_resource_list_from_drone(webclient: WebClient, uid_filter: str = None) -> List[Resource]:
    res_list: List[Resource] = []
    for media in webclient.get_media_list(media_type='photo'):
        for resource in media.get("resources"):
            # ignore resource if media_id or resource_id does not match
            if (
                uid_filter
                and uid_filter != media.get('media_id')
                and uid_filter != resource.get("resource_id")
            ):
                continue
            res_list.append(RemoteResource(resource, webclient))
    return res_list


def _get_ca_cert_path():
    return os.path.join(tools.locate_share_dir(), "ca-anafi-ai.pem")


def _verify_resource_list(
    res_list: List[Resource],
    tmpdirname: str,
    certificate: Certificate,
    log: bool = True,
    skip: bool = False,
) -> Dict:
    ok_count = 0
    ko_count = 0
    skip_count = 0
    output_list: Dict[str, Any] = {}
    output_list["resources"] = {}
    for res in res_list:
        output_node: Dict[str, Any] = {}
        res.set_crt(certificate)
        res.load(tmpdirname)
        try:
            ret = res.verify(tmpdirname)
            output = "valid signature" if ret else "invalid signature"
        except UnsignedResourceException:
            if not skip:
                skip_count += 1
                if log:
                    tools.format_output(res.res_uid, logging.WARNING, "no signature file")
                output_node["signed"] = False
        else:
            output_node["signed"] = True
            if ret:
                if log:
                    tools.format_output(res.res_uid, logging.INFO, "valid signature")
                ok_count = ok_count + 1
                output_node["valid_signature"] = True
            else:
                if log:
                    tools.format_output(res.res_uid, logging.ERROR, output)
                ko_count = ko_count + 1
                output_node["valid_signature"] = False
                output_node["reason"] = output
        output_list["resources"][str(res)] = output_node
    # after iterating
    total_count = ok_count + ko_count + skip_count
    LOGGER.info(f"Done. {total_count} files processed")
    output_list["ok_count"] = ok_count
    if ok_count:
        LOGGER.info(f"{tools.index_to_str(ok_count, total_count)} files have valid signature")
    output_list["ko_count"] = ko_count
    if ko_count:
        LOGGER.error(f"{tools.index_to_str(ko_count, total_count)} files have issues")
    output_list["unsigned_count"] = skip_count
    if skip_count and not skip:
        LOGGER.warning(f"{tools.index_to_str(skip_count, total_count)} files don't have signature")
    return output_list


def _verify(
    tmpdirname: str, crt_path: str, res_list: List[Resource], log: bool, skip_unsigned: bool
) -> Optional[Dict]:

    LOGGER.info("Verifying drone certificate")
    drone_cert = Certificate(crt_path)
    ca_cert = Certificate(_get_ca_cert_path(), trusted=True)
    if not ca_cert.verify_certificate(drone_cert):
        if log:
            tools.format_output(os.path.basename(crt_path), logging.ERROR, "invalid signature")
        return None
    if log:
        tools.format_output(os.path.basename(crt_path), logging.INFO, "valid signature")

    LOGGER.info("Verifying signatures")
    return _verify_resource_list(res_list, tmpdirname, drone_cert, log=log, skip=skip_unsigned)


def verify_on_disk(
    res_path: str,
    crt_path: str,
    sig_path: str = None,
    log: bool = True,
    skip_unsigned: bool = False,
) -> Optional[Dict]:
    """
    Verify media signatures on disk.

    Parameters:
        res_path (str): the resource file or directory path
        crt_path (str): the drone certificate file path
        sig_path (str): the signature file path
        log (bool): whether to log each entry
        skip_unsigned (bool): whether to skip unsigned media
    Returns:
        (dict): the verify result for each resource
    """
    with tempfile.TemporaryDirectory() as tmpdirname:
        res_list = _get_resource_list_from_path(res_path, sig_path)
        if not res_list:
            return None
        return _verify(tmpdirname, crt_path, res_list, log, skip_unsigned)


def verify_on_remote(
    ip_list=[C.ADB_DEFAULT_IP_RNDIS, C.ADB_DEFAULT_IP_WIFI],
    uid_filter=None,
    log=True,
    skip_unsigned=False,
) -> Optional[Dict]:
    """
    Verify media signatures on remote.

    Parameters:
        ip_list ([str]): the drone IP list
        uid_filter (str): an optional media or resource UID filter
        log (bool): whether to log each entry
        skip_unsigned (bool): whether to skip unsigned media
    Returns:
        (dict): the verify result for each resource
    """
    LOGGER.info("Connecting to drone REST API")
    webclient = WebClient(ip_list)
    if not webclient:
        LOGGER.error("Drone REST API not reachable")
        return None
    with tempfile.TemporaryDirectory() as tmpdirname:
        res_list = _get_resource_list_from_drone(webclient, uid_filter)
        crt_path = os.path.join(tmpdirname, "drone.der")
        if not webclient.download_drone_cert(crt_path):
            LOGGER.error("Unable to download certificate")
            return None
        return _verify(tmpdirname, crt_path, res_list, log, skip_unsigned)


def verify_single(res_path: str, crt_path: str, sig_path: str = None) -> bool:
    """
    Verify that a media signature is authentic.

    Parameters:
        res_path (str): the resource file path
        crt_path (str): the drone certificate file path
        sig_path (str): the signature file path
    Returns:
        (bool): whether the signature is authentic or not
    """
    if not os.path.isfile(res_path):
        LOGGER.error("Resource must be a file")
        raise ValueError
    out_dict = verify_on_disk(res_path, crt_path, sig_path)
    if not out_dict:
        return False
    if len(out_dict.get("resources", tuple())) != 1:
        LOGGER.error(f"Bad length ({len(out_dict)}, expecting 1)")
        return False
    val = list(out_dict.get("resources", {}).values())[0]
    if not val.get("signed"):
        # unsigned
        return False
    return val.get("valid_signature", False)
