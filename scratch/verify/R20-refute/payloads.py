import zendriver, sys
from zendriver.core.keys import KeyEvents, KeyPressEvent, SpecialKeys
print("zendriver from", zendriver.__file__, sys.version.split()[0])
for t in ["abc\n", "abc\r", "abc\r\n", "a\tb c"]:
    p = KeyEvents.from_text(t, KeyPressEvent.CHAR)
    print(repr(t), [(x["type_"], x["text"]) for x in p])
print("SpecialKeys.ENTER DOWN_AND_UP:", [(x["type_"], x["text"], x["key"], x["windows_virtual_key_code"]) for x in KeyEvents(SpecialKeys.ENTER).to_cdp_events(KeyPressEvent.DOWN_AND_UP)])
print("from_text DOWN_AND_UP 'a\\n':", [(x["type_"], x["text"], x["key"]) for x in KeyEvents.from_text("a\n", KeyPressEvent.DOWN_AND_UP)])
