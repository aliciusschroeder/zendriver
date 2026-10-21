import zendriver
print("zendriver from", zendriver.__file__)
from zendriver import KeyEvents, KeyPressEvent, SpecialKeys, KeyModifiers

def summary(evs):
    return [(e["type_"], e["key"], e["code"], e["text"], e["modifiers"]) for e in evs]

# A10.10 reuse
ev = KeyEvents("A")
p1 = ev.to_cdp_events(KeyPressEvent.DOWN_AND_UP)
p2 = ev.to_cdp_events(KeyPressEvent.DOWN_AND_UP)
print("A10.10 first :", summary(p1))
print("A10.10 second:", summary(p2))
ev = KeyEvents("!")
print("A10.10 '!' 1st:", [e["text"] for e in ev.to_cdp_events(KeyPressEvent.DOWN_AND_UP)], "2nd:", [e["text"] for e in ev.to_cdp_events(KeyPressEvent.DOWN_AND_UP)])
# A10.9 ordering
print("A10.9 Ctrl+Enter:", summary(KeyEvents.from_mixed_input([(SpecialKeys.ENTER, KeyModifiers.Ctrl)])))
print("A10.9 'A':", summary(KeyEvents.from_mixed_input(["A"])))
print("A10.9 Ctrl+Shift+a:", summary(KeyEvents.from_mixed_input([("a", KeyModifiers.Ctrl | KeyModifiers.Shift)])))
# A10.11
print("A10.11 SPACE:", summary(KeyEvents(SpecialKeys.SPACE).to_cdp_events(KeyPressEvent.DOWN_AND_UP)))
# A10.5 what send_keys(str) generates
for s in ["👍", "👍🏽", "🇩🇪", "👨‍👩‍👧‍👦", "é", "ñ", "é", "क्षि"]:
    evs = KeyEvents.from_text(s, KeyPressEvent.CHAR)
    print("A10.5", repr(s), "utf16=", len(s.encode("utf-16-le"))//2, summary(evs))
