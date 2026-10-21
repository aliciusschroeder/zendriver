"""Browser-free helpers: build cdp.dom.Node trees and a fake Tab.send."""

from __future__ import annotations

from collections.abc import Callable, Generator
from typing import Any

import zendriver as zd
from zendriver.core.connection import ProtocolException

cdp = zd.cdp


def make_node(
    node_id: int,
    node_name: str,
    *,
    children: list[cdp.dom.Node] | None = None,
    content_document: cdp.dom.Node | None = None,
    shadow_roots: list[cdp.dom.Node] | None = None,
    attributes: list[str] | None = None,
    parent_id: int | None = None,
    node_value: str = "",
) -> cdp.dom.Node:
    if node_name == "#document":
        node_type = 9
    elif node_name == "#text":
        node_type = 3
    elif node_name == "#document-fragment":
        node_type = 11
    else:
        node_type = 1
    node = cdp.dom.Node(
        node_id=cdp.dom.NodeId(node_id),
        backend_node_id=cdp.dom.BackendNodeId(node_id),
        node_type=node_type,
        node_name=node_name,
        local_name="" if node_type != 1 else node_name.lower(),
        node_value=node_value,
        parent_id=cdp.dom.NodeId(parent_id) if parent_id is not None else None,
        child_node_count=len(children) if children is not None else 0,
        children=children,
        attributes=attributes,
        content_document=content_document,
        shadow_roots=shadow_roots,
    )
    return node


def link(parent: cdp.dom.Node) -> cdp.dom.Node:
    """set parent_id on every descendant (children, shadow roots, content docs)."""
    for child in parent.children or []:
        child.parent_id = parent.node_id
        link(child)
    for sr in parent.shadow_roots or []:
        sr.parent_id = parent.node_id
        link(sr)
    if parent.content_document is not None:
        link(parent.content_document)
    return parent


def protocol_error(message: str) -> ProtocolException:
    return ProtocolException({"message": message, "code": -32000})


Handler = Callable[[dict[str, Any]], Any]


def make_tab(monkeypatch: Any, handlers: dict[str, Handler]) -> tuple[zd.Tab, list[dict[str, Any]]]:
    sent: list[dict[str, Any]] = []

    async def send(
        cdp_obj: Generator[dict[str, Any], dict[str, Any], Any],
        _is_update: bool = False,
    ) -> Any:
        command = next(cdp_obj)
        sent.append(command)
        method = command["method"]
        if method in handlers:
            result = handlers[method](command.get("params", {}))
            if hasattr(result, "__await__"):
                result = await result
            if isinstance(result, Exception):
                raise result
            return result
        if method in ("DOM.disable", "DOM.discardSearchResults", "DOM.removeNode"):
            return None
        if method == "DOM.resolveNode":
            return cdp.runtime.RemoteObject(
                type_="object",
                object_id=cdp.runtime.RemoteObjectId(
                    f"obj-{command['params'].get('backendNodeId')}"
                ),
            )
        raise AssertionError(f"Unexpected CDP command: {method}")

    tab = zd.Tab.__new__(zd.Tab)
    monkeypatch.setattr(tab, "send", send)
    return tab, sent
