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
import abc
import os
from typing import Optional

from . import tools
from .webclient import WebClient
from .certificate import Certificate


LOGGER = logging.getLogger(__name__)


class InvalidResourceException(Exception):
    """
    An invalid resource exception.
    """


class UnsignedResourceException(Exception):
    """
    An unsigned resource exception.
    """


class Resource:
    """
    A media resource that can be signed.
    """

    def __init__(self) -> None:
        self.verified = False
        self.res_uid: str
        self.res_path: str
        self.sig_path: str
        self.certificate: Optional[Certificate] = None
        self.has_sig = False

    @abc.abstractmethod
    def load(self, tmpdir: str) -> None:
        """
        Load a resource.
        """

    def set_crt(self, certificate: Certificate) -> None:
        """
        Set the certificate file path to a resource.
        """
        self.certificate = certificate

    def __str__(self) -> str:
        return self.res_uid

    def is_verified(self) -> bool:
        return self.verified

    def verify(self, tmpdir: str) -> bool:
        """
        Verify a resource.
        """
        if not self.has_sig or not os.path.isfile(self.sig_path):
            raise UnsignedResourceException("Missing signature")
        if not os.path.isfile(self.res_path):
            raise InvalidResourceException("Missing resource")
        if not self.certificate:
            raise InvalidResourceException("Missing cert")
        if not os.path.isdir(tmpdir):
            raise InvalidResourceException("Invalid output directory")
        self.verified = self.certificate.verify_signature(self.res_path, self.sig_path)
        return self.verified


class RemoteResource(Resource):
    """
    A media resource that is available on remote.
    """

    def __init__(self, json: dict, webclient: WebClient) -> None:
        super().__init__()
        self.res_uid = json.get("resource_id", "")
        self.res_url = json.get("url", "")
        self.sig_url = json.get("signature", "")
        self.has_sig = self.sig_url
        self.webclient = webclient

    def load(self, tmpdir: str) -> None:
        if not self.has_sig:
            LOGGER.debug(f"Skipping {self.res_uid}: no signature")
            return
        self.res_path = os.path.join(tmpdir, self.res_uid)
        self.sig_path = os.path.join(tmpdir, os.path.basename(self.sig_url))
        self.webclient.download_media(self.res_uid, self.res_url, self.res_path)
        self.webclient.download_media(self.res_uid, self.sig_url, self.sig_path)


class LocalResource(Resource):
    """
    A media resource that is available locally.
    """

    def __init__(self, res_path: str, sig_path: Optional[str] = None) -> None:
        super().__init__()
        self.res_path = res_path
        if not sig_path:
            sig_path = tools.media_file_to_sig(self.res_path)
        if not sig_path:
            raise InvalidResourceException("Unknown signature")
        self.sig_path = sig_path
        self.has_sig = os.path.isfile(self.sig_path)

    def load(self, tmpdir: str) -> None:
        self.res_uid = os.path.basename(self.res_path)
