"""Product-controlled loopback model boundary. Synthetic operation and receipt references only."""
import json
from urllib.error import HTTPError
from urllib.request import Request, urlopen


def exact_result(body, expected_call, receipt):
    tool=[m for m in body["messages"] if m["role"]=="tool"]
    calls=[c for m in body["messages"] if m["role"]=="assistant" for c in m.get("tool_calls",[])]
    if len(tool)!=1 or len(calls)!=1 or not receipt or not expected_call:
        return False
    raw=tool[0].get("content")
    if isinstance(raw,list):
        raw=next((p["text"] for p in raw if p.get("type")=="text"),None)
    try:
        value=json.loads(raw)
    except (TypeError,ValueError):
        value=raw
    return (value==receipt and calls[0]["id"]==expected_call and tool[0].get("tool_call_id")==expected_call
            and calls[0]["function"]["name"]=="async_operation")


def forward(handler,db,body,raw,destination):
    # In this synthetic trust domain authorized infrastructure can handle internal references.
    # The same product transaction orders revocation vs the external POST. No cross-domain IAM claim.
    op=next(m["content"] for m in body["messages"] if m["role"]=="user")
    if isinstance(op,list):
        op=next(p["text"] for p in op if p["type"]=="text")
    db.execute("begin immediate")
    row=db.execute("select * from ops where op=?",(op,)).fetchone()
    followup=any(m["role"]=="tool" for m in body["messages"])
    allowed=bool(row and not row["canceled"] and row["version"]==row["reader"]==1 and
                 (not followup or exact_result(body,row["call_id"],row["receipt"])))
    db.execute("insert into model_attempts(op,allowed,body) values(?,?,?)",(op,allowed,raw.decode()))
    if not allowed:
        db.commit()
        return handler.reply({"error":"model outbound refused"},403,prohibit_retry=True)
    # Only the trusted product gateway resolves the opaque prompt reference.
    external=json.loads(raw)
    external["messages"].insert(0,{"role":"system","content":row["prompt_private"]})
    req=Request(destination+"/v1/chat/completions",data=json.dumps(external).encode(),headers={"Content-Type":"application/json"})
    try:
        res=urlopen(req,timeout=20)
    except HTTPError as exc:
        res=exc
    with res:
        data=res.read()
        if res.status==200 and not followup:
            for line in data.decode().splitlines():
                if line.startswith("data: {"):
                    delta=json.loads(line[6:])["choices"][0]["delta"]
                    for call in delta.get("tool_calls",[]):
                        if call.get("id"):
                            db.execute("update ops set call_id=? where op=?",(call["id"],op))
        db.commit()
        handler.send_response(res.status)
        handler.send_header("Content-Type",res.headers["Content-Type"])
        if res.headers.get("x-should-retry"):
            handler.send_header("x-should-retry",res.headers["x-should-retry"])
        handler.send_header("Content-Length",str(len(data)))
        handler.end_headers()
        handler.wfile.write(data)
