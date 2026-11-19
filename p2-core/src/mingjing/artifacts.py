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
        self.root.mkdir(parents=True, mode=0o700, exist_ok=True)
        target = self.root / digest
        with NamedTemporaryFile(dir=self.root) as stream:
            stream.write(data)
            stream.flush()
            try:
                target.hardlink_to(stream.name)
            except FileExistsError:
                self.read(digest)
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
