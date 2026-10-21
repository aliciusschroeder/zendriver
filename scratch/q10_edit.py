import pathlib, sys
p = pathlib.Path(sys.argv[1])
s = p.read_text()
old_start = s.index("def make_search_recording_tab(")
old_end = s.index("async def test_query_selector_all_include_frames_queries_nested_iframe_documents(")
new = '''def make_search_recording_tab(
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[zd.Tab, list[tuple[str, str]], object]:
    # both searches match anything, so `calls` shows which one wait_for used
    calls: list[tuple[str, str]] = []
    match = object()

    async def query_selector(selector: str, *args: Any, **kwargs: Any) -> object:
        calls.append(("query_selector", selector))
        return match

    async def find_element_by_text(text: str, *args: Any, **kwargs: Any) -> object:
        calls.append(("find_element_by_text", text))
        return match

    tab = zd.Tab.__new__(zd.Tab)
    monkeypatch.setattr(tab, "query_selector", query_selector)
    monkeypatch.setattr(tab, "find_element_by_text", find_element_by_text)
    return tab, calls, match


async def test_call_with_text_searches_by_text(monkeypatch: pytest.MonkeyPatch) -> None:
    tab, calls, match = make_search_recording_tab(monkeypatch)

    by_keyword = await tab(text="Apples", timeout=1)
    by_position = await tab("Apples", timeout=1)

    assert calls == [("find_element_by_text", "Apples")] * 2
    assert by_keyword is match
    assert by_position is match


async def test_call_with_selector_queries_css(monkeypatch: pytest.MonkeyPatch) -> None:
    tab, calls, match = make_search_recording_tab(monkeypatch)

    result = await tab(selector="li", timeout=1)

    assert calls == [("query_selector", "li")]
    assert result is match


'''
p.write_text(s[:old_start] + new + s[old_end:])
