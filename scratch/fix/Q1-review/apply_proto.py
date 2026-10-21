"""Temporarily add a listener-revival check to Connection._send_transaction
(working tree only, reverted with git checkout afterwards)."""

p = "/home/user/zendriver/.claude/worktrees/wf_453a9023-a6b-14/zendriver/core/connection.py"
s = open(p).read()
old = """    async def _send_transaction(self, tx: Transaction[Any]) -> None:
        if self.websocket is None:
            raise ProtocolException("connection was closed")
        try:"""
assert old in s
s = s.replace(
    old,
    """    async def _send_transaction(self, tx: Transaction[Any]) -> None:
        if self.websocket is None:
            raise ProtocolException("connection was closed")
        reader = self._session_parent or self
        if reader.websocket is not None and (
            not reader.listener or not reader.listener.running
        ):
            reader.listener = Listener(reader)
        try:""",
)
open(p, "w").write(s)
print("applied")
