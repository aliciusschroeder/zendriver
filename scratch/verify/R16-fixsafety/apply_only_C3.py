import sys, pathlib
p = pathlib.Path(sys.argv[1])
s = p.read_text()

def sub(old, new):
    global s
    assert s.count(old) == 1, (s.count(old), old)
    s = s.replace(old, new)

# SEED-C3: a cancelled (or failed) send must not leave its transaction behind
sub('''        await self._send_transaction(tx)
        try:
            return await tx
        except ProtocolException as e:
            e.message = e.message or ""
            e.message += f"\\ncommand:{tx.method}\\nparams:{tx.params}"
            raise e
''', '''        await self._send_transaction(tx)
        try:
            return await tx
        except ProtocolException as e:
            e.message = e.message or ""
            e.message += f"\\ncommand:{tx.method}\\nparams:{tx.params}"
            raise e
        finally:
            # the listener pops answered transactions; one whose caller was
            # cancelled (e.g. by asyncio.wait_for) must not stay behind
            self.mapper.pop(tx.id, None)
''')

p.write_text(s)
print('patched', p)
