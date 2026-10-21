import zendriver
from zendriver.core.keys import KeyEvents, KeyPressEvent, SpecialKeys, KeyModifiers
import grapheme
print("zendriver:", zendriver.__file__)
for s in ['\U0001F44D\U0001F3FD', '\U0001F1E9\U0001F1EA', '\U0001F468‍\U0001F469‍\U0001F467‍\U0001F466']:
    print(repr(s), list(grapheme.graphemes(s)), [p['text'] for p in KeyEvents.from_text(s, KeyPressEvent.CHAR)])
ev = KeyEvents('A')
p1 = ev.to_cdp_events(KeyPressEvent.DOWN_AND_UP)
print("ev.key after first:", repr(ev.key), "modifiers", ev.modifiers)
p2 = ev.to_cdp_events(KeyPressEvent.DOWN_AND_UP)
print("p1:", [(p['type_'], p['key'], p['text'], p['modifiers']) for p in p1])
print("p2:", [(p['type_'], p['key'], p['text'], p['modifiers']) for p in p2])
ev = KeyEvents('!')
ev.to_cdp_events(KeyPressEvent.DOWN_AND_UP)
print("'!' second:", [(p['type_'], p['key'], p['text']) for p in ev.to_cdp_events(KeyPressEvent.DOWN_AND_UP)])
ev = KeyEvents(SpecialKeys.ENTER)
ev.to_cdp_events(KeyPressEvent.CHAR)
print("SpecialKeys ENTER after CHAR: key=", repr(ev.key), type(ev.key))
print("second CHAR:", ev.to_cdp_events(KeyPressEvent.CHAR))
print("then DOWN_AND_UP:", [(p['type_'], p['key'], p['code']) for p in ev.to_cdp_events(KeyPressEvent.DOWN_AND_UP)])
print("SPACE events:", [(p['type_'], p['key'], p['code'], p['windows_virtual_key_code']) for p in KeyEvents(SpecialKeys.SPACE).to_cdp_events(KeyPressEvent.DOWN_AND_UP)])
print("Ctrl+Enter:", [(p['type_'], p['key'], p['modifiers']) for p in KeyEvents(SpecialKeys.ENTER, KeyModifiers.Ctrl).to_cdp_events(KeyPressEvent.DOWN_AND_UP)])
print("Ctrl+Shift+a:", [(p['type_'], p['key'], p['modifiers']) for p in KeyEvents('a', KeyModifiers.Ctrl|KeyModifiers.Shift).to_cdp_events(KeyPressEvent.DOWN_AND_UP)])
