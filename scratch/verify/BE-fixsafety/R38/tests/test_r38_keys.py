import pathlib
import shutil

import pytest

import zendriver
from zendriver import KeyEvents, KeyModifiers, KeyPressEvent, SpecialKeys

print("zendriver imported from", zendriver.__file__)

EMOJIS = [
    "\U0001f44d\U0001f3fd",  # thumbs up, skin tone (4 utf-16 units)
    "\U0001f1e9\U0001f1ea",  # flag (4)
    "\U0001f468‍\U0001f469‍\U0001f467‍\U0001f466",  # family ZWJ (11)
]


def _units(s: str) -> int:
    return len(s.encode("utf-16-le")) // 2


def test_zendriver_location() -> None:
    print("zendriver imported from", zendriver.__file__)


@pytest.mark.parametrize("text", EMOJIS + ["á̂̃"])
def test_char_payload_text_fits_chrome_limit(text: str) -> None:
    payloads = KeyEvents.from_text("x" + text + "y", KeyPressEvent.CHAR)
    assert "".join(p["text"] or "" for p in payloads) == "x" + text + "y"
    # chrome's Input.dispatchKeyEvent rejects text of 4+ utf-16 code units
    assert all(_units(p["text"] or "") <= 3 for p in payloads), [
        p["text"] for p in payloads
    ]


def _seq(payloads):
    return [(p["type_"], p["key"], p["modifiers"]) for p in payloads]


def test_main_key_released_before_modifiers_in_reverse_order() -> None:
    payloads = KeyEvents.from_mixed_input(
        [(SpecialKeys.ENTER, KeyModifiers.Ctrl | KeyModifiers.Shift)]
    )
    seq = _seq(payloads)
    assert seq[0][:2] == ("keyDown", "Control")
    assert seq[1][:2] == ("keyDown", "Shift")
    assert seq[2][:2] == ("keyDown", "\r")
    # the main key goes up while the modifiers are still held
    assert seq[3] == ("keyUp", "\r", KeyModifiers.Ctrl | KeyModifiers.Shift)
    # then the modifiers, in reverse order
    assert seq[4][:2] == ("keyUp", "Shift")
    assert seq[5][:2] == ("keyUp", "Control")


def test_shift_letter_keyup_is_uppercase() -> None:
    seq = _seq(KeyEvents.from_mixed_input(["A"]))
    assert seq == [
        ("keyDown", "Shift", KeyModifiers.Shift),
        ("keyDown", "A", KeyModifiers.Shift),
        ("keyUp", "A", KeyModifiers.Shift),
        ("keyUp", "Shift", 0),
    ]


@pytest.mark.parametrize("key", ["A", "!", "_", "\n", SpecialKeys.SPACE])
def test_reusing_key_events_gives_same_events(key) -> None:
    ev = KeyEvents(key)
    first = ev.to_cdp_events(KeyPressEvent.DOWN_AND_UP)
    second = ev.to_cdp_events(KeyPressEvent.DOWN_AND_UP)
    assert first == second
    assert ev.key == key


def test_char_path_does_not_mutate_key() -> None:
    ev = KeyEvents(SpecialKeys.ENTER)
    ev.to_cdp_events(KeyPressEvent.CHAR)
    assert ev.key is SpecialKeys.ENTER


@pytest.mark.parametrize("make", [
    lambda: KeyEvents(SpecialKeys.SPACE).to_cdp_events(KeyPressEvent.DOWN_AND_UP),
    lambda: KeyEvents.from_mixed_input([" "]),
])
def test_space_uses_dom_code_space(make) -> None:
    payloads = make()
    assert [p["code"] for p in payloads] == ["Space", "Space"]
    assert [p["key"] for p in payloads] == [" ", " "]


HTML = """<html><body><textarea id=t></textarea><input id=i><div id=c contenteditable></div><script>
window.log=[];
for (const ev of ['keydown','keyup']) document.addEventListener(ev, e => log.push(e.type+':'+e.key+':'+e.code+':'+e.ctrlKey+':'+e.shiftKey), true);
</script></body></html>"""


@pytest.fixture
async def page(tmp_path: pathlib.Path):
    p = tmp_path / "k.html"
    p.write_text(HTML)
    browser = await zendriver.start(headless=True)
    try:
        yield await browser.get(p.as_uri())
    finally:
        await browser.stop()


async def test_chrome_emoji_typing_and_key_log(page) -> None:
    for sel, getter in [("#t", "(e)=>e.value"), ("#i", "(e)=>e.value"), ("#c", "(e)=>e.textContent")]:
        elem = await page.select(sel)
        text = "x" + "".join(EMOJIS) + "á̂̃y"
        await elem.send_keys(text)
        assert await elem.apply(getter) == text, sel
    elem = await page.select("#t")
    await page.evaluate("window.log=[]")
    await elem.send_keys(KeyEvents.from_mixed_input([(SpecialKeys.ENTER, KeyModifiers.Ctrl)]))
    await elem.send_keys(SpecialKeys.SPACE)
    log = await page.evaluate("window.log")
    assert log == [
        "keydown:Control:ControlLeft:true:false",
        "keydown:Enter:Enter:true:false",
        "keyup:Enter:Enter:true:false",
        "keyup:Control:ControlLeft:false:false",
        "keydown: :Space:false:false",
        "keyup: :Space:false:false",
    ], log
