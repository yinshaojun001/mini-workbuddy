import asyncio
from pathlib import Path

from app.runtime.approvals import ApprovalBroker
from app.runtime.engine import AgentEngine


def test_session_crud(client):
    created = client.post("/api/sessions", json={"agent_id": "main-agent", "title": "第一次会话"})
    assert created.status_code == 201
    session = created.json()
    assert client.get("/api/sessions").json()[0]["id"] == session["id"]
    assert client.get(f"/api/sessions/{session['id']}/messages").json() == []
    assert client.delete(f"/api/sessions/{session['id']}").status_code == 204


class FakeAdapter:
    def __init__(self, responses):
        self.responses = iter(responses)

    async def complete(self, _model, _messages, _tools):
        return next(self.responses)


async def collect(engine, **kwargs):
    return [event async for event in engine.run(**kwargs)]


async def test_engine_reads_file_without_approval(tmp_path: Path):
    (tmp_path / "note.txt").write_text("本地内容", encoding="utf-8")
    adapter = FakeAdapter(
        [
            {"content": "", "tool_calls": [{"id": "call-1", "name": "read_file", "arguments": {"path": "note.txt"}}]},
            {"content": "已读取。", "tool_calls": []},
        ]
    )
    engine = AgentEngine(adapter, ApprovalBroker(), max_rounds=4)

    events = await collect(
        engine,
        model={},
        messages=[{"role": "user", "content": "读文件"}],
        tools=[{"id": "read_file", "enabled": True}],
        workspace=tmp_path,
    )

    assert any(event["type"] == "tool.completed" for event in events)
    assert not any(event["type"] == "approval.required" for event in events)
    assert events[-1]["type"] == "run.completed"


async def test_engine_waits_for_write_approval(tmp_path: Path):
    broker = ApprovalBroker()
    adapter = FakeAdapter(
        [
            {"content": "", "tool_calls": [{"id": "call-2", "name": "write_file", "arguments": {"path": "out.txt", "content": "完成"}}]},
            {"content": "文件已写入。", "tool_calls": []},
        ]
    )
    engine = AgentEngine(adapter, broker, max_rounds=4)
    events = []

    async def consume():
        async for event in engine.run(
            model={},
            messages=[{"role": "user", "content": "写文件"}],
            tools=[{"id": "write_file", "enabled": True}],
            workspace=tmp_path,
        ):
            events.append(event)

    task = asyncio.create_task(consume())
    for _ in range(50):
        if broker.pending:
            break
        await asyncio.sleep(0.01)
    approval_id = next(iter(broker.pending))
    broker.resolve(approval_id, True)
    await task

    assert (tmp_path / "out.txt").read_text() == "完成"
    assert any(event["type"] == "approval.required" for event in events)
    assert events[-1]["type"] == "run.completed"


async def test_engine_rejected_write_does_not_touch_disk(tmp_path: Path):
    broker = ApprovalBroker()
    adapter = FakeAdapter(
        [
            {"content": "", "tool_calls": [{"id": "call-3", "name": "write_file", "arguments": {"path": "blocked.txt", "content": "不应写入"}}]},
            {"content": "操作已取消。", "tool_calls": []},
        ]
    )
    engine = AgentEngine(adapter, broker, max_rounds=4)

    async def reject_when_ready():
        while not broker.pending:
            await asyncio.sleep(0.01)
        broker.resolve(next(iter(broker.pending)), False)

    reject_task = asyncio.create_task(reject_when_ready())
    events = await collect(
        engine,
        model={},
        messages=[{"role": "user", "content": "写文件"}],
        tools=[{"id": "write_file", "enabled": True}],
        workspace=tmp_path,
    )
    await reject_task

    assert not (tmp_path / "blocked.txt").exists()
    assert any(event["type"] == "approval.resolved" and event["data"]["allowed"] is False for event in events)

