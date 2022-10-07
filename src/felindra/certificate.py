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
import pathlib

from Crypto.Hash import SHA256
from Crypto.PublicKey import ECC
from Crypto.Signature import DSS
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization


LOGGER = logging.getLogger(__name__)


class InvalidCertificateError(Exception):
    pass


class Certificate:
    def __init__(self, path: str, trusted: bool = False) -> None:
        self.verified = trusted
        if not os.path.isfile(path):
            raise FileNotFoundError
        ext = pathlib.Path(path).suffix
        if ext == ".der":
            self.cert = Certificate._load_from_der(path)
        if ext == ".pem":
            self.cert = Certificate._load_from_pem(path)
        if not self.cert:
            raise InvalidCertificateError

    @staticmethod
    def _load_from_der(path: str) -> x509.Certificate:
        # Known issue of loading DER certificate with trailing data
        # https://pythontechworld.com/issue/pyca/cryptography/7340
        # Workaround: strip all '0xff' bytes at the end of the file, then:
        # - attempt to load certificate,
        # - if that doesn't work, append one byte and retry until the end of file is reached
        with open(path, "rb") as file:
            padded_data = file.read()
            padded_len = 0
            for i in reversed(range(0, len(padded_data))):
                if padded_data[i] != 0xFF:
                    padded_len = i
                    break
            for i in range(padded_len, len(padded_data)):
                try:
                    crt = x509.load_der_x509_certificate(padded_data[0:i], default_backend())
                except ValueError:
                    continue
                else:
                    return crt
            raise InvalidCertificateError

    @staticmethod
    def _load_from_pem(path: str) -> x509.Certificate:
        with open(path, "rb") as file:
            return x509.load_pem_x509_certificate(file.read(), default_backend())

    def _save_as(
        self, out_path: str, out_format: serialization.Encoding = serialization.Encoding.PEM
    ) -> bool:
        if not self.cert:
            return False
        with open(out_path, "wb") as file:
            file.write(self.cert.public_bytes(out_format))
        return True

    def save_as_pem(self, out_path: str) -> bool:
        return self._save_as(out_path, out_format=serialization.Encoding.PEM)

    def save_as_der(self, out_path: str) -> bool:
        return self._save_as(out_path, out_format=serialization.Encoding.DER)

    def is_verified(self) -> bool:
        return self.verified

    def get_bytes(self, out_format: serialization.Encoding = serialization.Encoding.DER) -> bytes:
        return self.cert.public_bytes(out_format)

    def verify_certificate(self, other: Certificate) -> bool:
        if not self.cert or not self.verified:
            return False
        try:
            key_auth = ECC.import_key(self.get_bytes())
            hsh = SHA256.new(other.cert.tbs_certificate_bytes)
            verifier = DSS.new(key_auth, "fips-186-3", encoding="der")
        except (ECC.UnsupportedEccFeature, ValueError) as err:
            LOGGER.debug(err)
        try:
            verifier.verify(hsh, other.cert.signature)
            other.verified = True
        except ValueError as err:
            other.verified = False
            LOGGER.debug(err)
        return other.verified

    def verify_signature(self, file_path: str, sig_path: str) -> bool:
        if not self.verified:
            return False
        try:
            with open(file_path, "rb") as file:
                hsh = SHA256.new(file.read())
                key = ECC.import_key(self.get_bytes())
                verifier = DSS.new(key, "fips-186-3", encoding="der")
        except (ECC.UnsupportedEccFeature, ValueError) as err:
            LOGGER.debug(err)
            return False
        try:
            with open(sig_path, "rb") as file:
                verifier.verify(hsh, file.read())
            return True
        except ValueError as err:
            LOGGER.debug(err)
            return False
