"""New adapter release retains the v1 reader and quarantines the retired array format."""
def encode(format_number, messages, operation, call):
    if format_number != 1:
        raise ValueError("cannot start a new legacy-format task")
    return {"schema": 1, "operation": operation, "call": call, "history": messages}


def decode(record):
    envelope = record["msg"]
    if record["checkpoint_version"] != 1 or not isinstance(envelope, dict):
        return None
    if (envelope.get("schema"), envelope.get("operation"), envelope.get("call")) != (1, record["op"], record["call"]):
        return None
    return envelope["history"]
