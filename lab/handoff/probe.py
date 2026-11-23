"""Experiment only. A bounded TCP write is the irreversible handoff; a delayed response is never inside its lock."""
import concurrent.futures
import hashlib
import json
import multiprocessing as mp
import os
import socket
import time
from pathlib import Path

import psycopg

TIMEOUT = 8
ROLES = ("model", "tool", "commit", "deliver")
ORDERS = ("revocation-first", "handoff-first", "stale-unlocked")


def connect():
    return psycopg.connect(os.environ["LAB_DSN"], options="-c lock_timeout=8000 -c statement_timeout=10000")


def receiver(channel):
    os.environ.pop("LAB_DSN", None)
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        listener.settimeout(TIMEOUT)
        channel.send(listener.getsockname())
        with listener.accept()[0] as peer:
            peer.settimeout(TIMEOUT)
            data = bytearray()
            while True:
                chunk = peer.recv(2048)
                if not chunk:
                    break
                data.extend(chunk)
                if len(data) > 2048:
                    raise ValueError("oversized experiment input")
            frame = bytes(data)
            channel.send({"bytes": len(frame), "frames": frame.count(b"\n"), "eof": True,
                          "sha256": hashlib.sha256(frame).hexdigest(), "frame": frame.decode().strip(),
                          "observed_ns": time.monotonic_ns()})
            if frame:
                if not channel.poll(TIMEOUT) or channel.recv() != "allow-reply":
                    raise TimeoutError("missing reply permit")
                peer.sendall(b"ack\n")


def receive(pipe):
    if not pipe.poll(TIMEOUT):
        raise TimeoutError("witness did not report")
    return pipe.recv()


def waiting(conn, waiter, holder):
    deadline = time.monotonic() + TIMEOUT
    while time.monotonic() < deadline:
        pids, = conn.execute("SELECT pg_blocking_pids(%s)", (waiter,)).fetchone()
        if holder in pids:
            return pids
        time.sleep(.015)
    raise TimeoutError(f"no database contention between {waiter} and {holder}")


def authority(conn, scope, lock):
    sql = "SELECT allowed FROM grant_state WHERE scope=%s"
    if lock:
        sql += " FOR SHARE"
    return conn.execute(sql, (scope,)).fetchone()[0]


def revoke(conn, scope):
    conn.execute("UPDATE grant_state SET allowed=false WHERE scope=%s", (scope,))
    conn.commit()
    return time.monotonic_ns()


def write_frame(sock, scope):
    # The first application byte and the rest of this short frame go out inside this call.
    sock.sendall((scope + "\n").encode())
    return time.monotonic_ns()


def attempted_send(conn, sock, scope):
    permitted = authority(conn, scope, True)
    handed = write_frame(sock, scope) if permitted else None
    conn.commit()
    return handed


def sample(role, order, index):
    scope = f"{role}-{order}-{index}"
    with connect() as admin:
        admin.execute("INSERT INTO grant_state VALUES (%s,true)", (scope,))
    ctx = mp.get_context("spawn")
    pipe, child = ctx.Pipe()
    peer = ctx.Process(target=receiver, args=(child,))
    peer.start()
    child.close()
    try:
        address = receive(pipe)
        with socket.create_connection(address, timeout=TIMEOUT) as sock, connect() as sender, connect() as revoker, connect() as monitor:
            monitor.autocommit = True
            sid, rid = sender.info.backend_pid, revoker.info.backend_pid
            held_by = []
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                if order == "revocation-first":
                    revoker.execute("UPDATE grant_state SET allowed=false WHERE scope=%s", (scope,))
                    future = pool.submit(attempted_send, sender, sock, scope)
                    held_by = waiting(monitor, sid, rid)
                    revoker.commit()
                    revoked = time.monotonic_ns()
                    handoff = future.result(timeout=TIMEOUT)
                elif order == "handoff-first":
                    assert authority(sender, scope, True)
                    future = pool.submit(revoke, revoker, scope)
                    held_by = waiting(monitor, rid, sid)
                    handoff = write_frame(sock, scope)
                    sender.commit()
                    revoked = future.result(timeout=TIMEOUT)
                else:
                    assert authority(sender, scope, False)
                    sender.commit()
                    revoked = revoke(revoker, scope)
                    handoff = write_frame(sock, scope)
            sock.shutdown(socket.SHUT_WR)
            observed = receive(pipe)
            assert authority(monitor, scope, False) is False
            expected_bytes = b"" if order == "revocation-first" else (scope + "\n").encode()
            assert observed["eof"] and observed["bytes"] == len(expected_bytes)
            assert observed["frames"] == expected_bytes.count(b"\n")
            assert observed["sha256"] == hashlib.sha256(expected_bytes).hexdigest()
            if order == "revocation-first":
                assert handoff is None and observed["frame"] == "" and rid in held_by
            else:
                assert observed["frame"] == scope and handoff is not None
                assert (handoff < revoked) if order == "handoff-first" else (revoked < handoff)
                if order == "handoff-first":
                    assert sid in held_by
                pipe.send("allow-reply")
                with sock.makefile("rb") as reader:
                    assert reader.readline(16) == b"ack\n"
            finished = time.monotonic_ns()
            return dict(scope=scope, order=order, role=role, sender=sid, revoker=rid, blockers=held_by,
                        handoff_ns=handoff, revoked_observed_ns=revoked, receiver=observed,
                        reply_or_eof_observed_ns=finished)
    finally:
        pipe.close()
        peer.join(TIMEOUT)
        if peer.is_alive():
            peer.terminate()
            peer.join(TIMEOUT)
            raise RuntimeError("witness failed to stop")
        if peer.exitcode:
            raise RuntimeError(f"witness exit {peer.exitcode}")


def main():
    from importlib import metadata
    with connect() as conn:
        conn.execute("CREATE TABLE grant_state(scope text PRIMARY KEY, allowed boolean NOT NULL)")
        server_version = conn.execute("SHOW server_version").fetchone()[0]
    dist = metadata.distribution("types-protobuf")
    licenses = {}
    for path in dist.files or []:
        if "licen" in str(path).lower() and path.name.lower().startswith(("license","copying")):
            data = Path(dist.locate_file(path)).read_bytes()
            licenses[str(path)] = [hashlib.sha256(data).hexdigest(), data.decode(errors="replace").splitlines()[:4]]
    print("GATE_ENV", json.dumps(dict(postgres=server_version, psycopg=metadata.version("psycopg"),
          stub_version=dist.version, license_expression=dist.metadata.get("License-Expression"), license_files=licenses)), flush=True)
    for i in range(2):
        for role in ROLES:
            for order in ORDERS:
                record = sample(role, order, i)
                print("GATE_RAW",json.dumps(record, sort_keys=True, separators=(",",":")),flush=True)
    print("GATE_EXIT 0",flush=True)


if __name__ == "__main__":
    main()
