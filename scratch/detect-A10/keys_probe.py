import grapheme
from zendriver import KeyEvents, KeyPressEvent, SpecialKeys, KeyModifiers
print("graphemes:", list(grapheme.graphemes("a\r\nb")))
for mode in (KeyPressEvent.CHAR, KeyPressEvent.DOWN_AND_UP):
    print(mode, "\\r\\n ->", KeyEvents.from_text("a\r\nb", mode))
print("\\n CHAR ->", KeyEvents.from_text("\n", KeyPressEvent.CHAR))
print("\\n DU ->", KeyEvents.from_text("\n", KeyPressEvent.DOWN_AND_UP))
k = KeyEvents("A")
print("reuse1", [(e['type_'], e['key'], e['modifiers']) for e in k.to_cdp_events(KeyPressEvent.DOWN_AND_UP)])
print("reuse2", [(e['type_'], e['key'], e['modifiers']) for e in k.to_cdp_events(KeyPressEvent.DOWN_AND_UP)])
print("SPACE", KeyEvents(SpecialKeys.SPACE).to_cdp_events(KeyPressEvent.DOWN_AND_UP))
print("ctrl+a", [(e['type_'], e['key'], e['text'], e['modifiers']) for e in KeyEvents.from_mixed_input([("a", KeyModifiers.Ctrl|KeyModifiers.Shift)])])
try:
    print(KeyEvents.from_mixed_input([("A", KeyModifiers.Ctrl)]))
except Exception as e: print("A+Ctrl:", repr(e))
print("enter", KeyEvents(SpecialKeys.ENTER).to_cdp_events(KeyPressEvent.DOWN_AND_UP))
print("empty", KeyEvents("").code)
