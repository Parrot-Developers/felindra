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
import os
from typing import Dict, List, Optional, Union
import requests

from . import constants as C


LOGGER = logging.getLogger(__name__)


class WebClient:
    """
    Represents a Web client that connects to the drone REST API.
    """

    def __init__(self, ip_addr_list: Union[str, List[str]]) -> None:
        self.pingable = False
        if not isinstance(ip_addr_list, list):
            ip_addr_list = [ip_addr_list]
        for self.ip_addr in ip_addr_list:
            self.url = f"http://{self.ip_addr}/"
            LOGGER.debug(f"Connecting to drone REST API at {self.url}")
            if self._is_pingable():
                self.pingable = True
                return

    def __bool__(self):
        return self.pingable

    def _is_pingable(self) -> bool:
        try:
            req = requests.get(self.url, stream=True, timeout=3)
            return req.status_code == 200
        except requests.exceptions.ConnectTimeout:
            return False

    @staticmethod
    def _download_file(url: str, out_path: str) -> bool:
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "wb") as file:
            req = requests.get(url, stream=True)
            if req.status_code != 200:
                return False
            total_length = req.headers.get("content-length")
            if total_length is None:  # no content length header
                file.write(req.content)
            else:
                dl_len = 0
                for data in req.iter_content(chunk_size=4096):
                    dl_len += len(data)
                    file.write(data)
            if not os.path.isfile(out_path):
                return False
            return True

    def download_drone_cert(self, out_path: str) -> bool:
        """
        Download the drone certificate.

        Parameters:
        out_path (str): the output directory

        Returns:
        (bool): whether the certificate was downloaded
        """
        LOGGER.debug("Downloading drone certificate")
        if not WebClient._download_file(self.url + C.WEBSERVER_API_DRONE_CERT, out_path):
            LOGGER.info("Unable to download drone certificate")
            return False
        LOGGER.debug(f"Drone certificate has been saved to '{out_path}'")
        return True

    def download_fdr(self, fdr_index: int, fdr_url: str, out_path: str) -> bool:
        """
        Download an FDR from the drone REST API.

        Parameters:
        fdr_index (str): the resource ID to download (for logging)
        fdr_url (str): the resource URL to fetch
        out_path (str): the output directory

        Returns:
        (bool): whether the FDR was downloaded
        """
        LOGGER.debug(f"Downloading FDR: {fdr_index}")
        if not WebClient._download_file(self.url + fdr_url, out_path):
            LOGGER.info(f"Unable to download FDR {fdr_index}")
            return False
        LOGGER.debug(f"FDR has been saved to '{out_path}'")
        return True

    def download_media(self, resource_id: str, resource_url: str, out_path: str) -> bool:
        """
        Download a media from the drone REST API.

        Parameters:
        resource_id (str): the resource ID to download (for logging)
        resource_url (str): the resource URL to fetch
        out_path (str): the output directory

        Returns:
        (bool): whether the media was downloaded
        """
        LOGGER.debug(f"Downloading media: {resource_id}")
        if not WebClient._download_file(self.url + resource_url, out_path):
            LOGGER.error(f"Unable to download media {resource_id}")
            return False
        LOGGER.debug(f"Media has been saved to '{out_path}'")
        return True

    def _get_content_list(self, rest_uri: str, content_label: Optional[str] = None) -> Dict:
        req = requests.get(self.url + rest_uri)
        if req.status_code != 200:
            LOGGER.error(f'Unable to get {content_label + " " if content_label else ""}list')
            return {}
        root = req.json()
        if not root:
            return {}
        return root

    def get_media_list(self, media_type: Optional[str] = None) -> Dict:
        """
        Retrieves the media list using the drone REST API.
        """
        url = C.WEBSERVER_API_MEDIAS
        if media_type:
            url += f'?media_type={media_type}'
        return self._get_content_list(url, "media")

    def get_fdr_list(self) -> Dict:
        """
        Retrieves the FDR list using the drone REST API.
        """
        return self._get_content_list(C.WEBSERVER_API_FDR, "FDR")
