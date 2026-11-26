import os
from hashlib import sha256
from pathlib import Path
from tempfile import NamedTemporaryFile
from uuid import uuid4

from .contracts import Fault


class BlobStore:
    def __init__(self, root: Path):
        self.root = root

    def write(self, data: bytes) -> str:
        if len(data) > 64 * 1024:
            raise Fault("artifact_too_large", 413)
        digest = sha256(data).hexdigest()
        if not self.root.is_dir():
            raise Fault("artifact_store_unavailable", 503)
        target = self.root / digest
        try:
            with NamedTemporaryFile(dir=self.root) as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
                try:
                    target.hardlink_to(stream.name)
                except FileExistsError:
                    self.read(digest)
            directory = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        except OSError as error:
            raise Fault("artifact_store_unavailable", 503) from error
        return digest

    def read(self, digest: str) -> bytes:
        try:
            data = (self.root / digest).read_bytes()
        except FileNotFoundError as error:
            raise Fault("artifact_unavailable", 503) from error
        if sha256(data).hexdigest() != digest:
            raise Fault("artifact_corrupt", 503)
        return data


def save_artifact(connection, blobs: BlobStore, task, data: bytes):
    digest = blobs.write(data)
    artifact = uuid4()
    connection.execute(
        "INSERT INTO artifacts VALUES (%s,%s,%s,1,%s,'text/plain',%s)",
        (artifact, task["tenant"], task["id"], digest, len(data)),
    )
    return str(artifact)
