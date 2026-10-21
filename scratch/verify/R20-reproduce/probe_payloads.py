import zendriver
from zendriver.core.keys import KeyEvents, KeyPressEvent, SpecialKeys
print("zendriver from", zendriver.__file__)
for t in ["a\nb", "a\rb", "a\r\nb", "\n"]:
    print(repr(t), "->", [p["text"] for p in KeyEvents.from_text(t, KeyPressEvent.CHAR)])
print("full payload for '\\n':", KeyEvents.from_text("\n", KeyPressEvent.CHAR))
print("SpecialKeys.ENTER DOWN_AND_UP texts:", [(p["type_"], p["text"]) for p in KeyEvents(SpecialKeys.ENTER).to_cdp_events(KeyPressEvent.DOWN_AND_UP)])
print("SPECIAL_KEY_CHAR_MAP[ENTER] =", repr(KeyEvents.SPECIAL_KEY_CHAR_MAP[SpecialKeys.ENTER]))
