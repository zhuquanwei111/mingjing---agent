"""Old adapter release: can produce both legacy-array and v1 object checkpoints."""
def encode(format_number, messages, operation, call):
    if format_number == 0:
        return [operation, call, messages]
    if format_number == 1:
        return {"schema": 1, "operation": operation, "call": call, "history": messages}
    raise ValueError("writer does not know this checkpoint format")


def decode(record):
    if record["checkpoint_version"] == 0:
        operation, call, messages = record["msg"]
        if (operation, call) == (record["op"], record["call"]):
            return messages
    if record["checkpoint_version"] == 1:
        return record["msg"]["history"]
    return None
