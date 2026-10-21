import pathlib, sys
p = pathlib.Path(sys.argv[1]) / "zendriver/core/tab.py"
s = p.read_text()

def rep(old, new):
    global s
    assert s.count(old) == 1, old
    s = s.replace(old, new)

# A5.6: collect iframe documents for the stale retry too, and do not drop iframe errors
rep('''        if not _node:
            # Returns all document node ids here
            doc = await self.send(cdp.dom.get_document(-1, True))
            if _include_frames:
                # Collect all iframe content_document nodes
                stack = [doc]
                while stack:
                    # pop off items to grab the nodes
                    node = stack.pop()
                    if node.content_document:
                        # save the nodes
                        content_doc_nodes.append(node.content_document)
                        stack.append(node.content_document)
                    if node.children:
                        #  add back child nodes to pop later on
                        stack.extend(node.children)

        else:
            doc = _node
            if _node.node_name == "IFRAME":
                doc = _node.content_document
                if doc is None:
                    return []  # cross-origin iframes block access to content_document, skip gracefully
        node_ids = []
''', '''        if not _node:
            # Returns all document node ids here
            doc = await self.send(cdp.dom.get_document(-1, True))
        else:
            doc = _node
            if _node.node_name == "IFRAME":
                doc = _node.content_document
                if doc is None:
                    return []  # cross-origin iframes block access to content_document, skip gracefully
        if _include_frames:
            # Collect all iframe content_document nodes
            stack = [doc]
            while stack:
                # pop off items to grab the nodes
                node = stack.pop()
                if node.content_document:
                    # save the nodes
                    content_doc_nodes.append(node.content_document)
                    stack.append(node.content_document)
                if node.children:
                    #  add back child nodes to pop later on
                    stack.extend(node.children)
        node_ids = []
''')
rep('''            if _include_frames:
                for cd_node in content_doc_nodes:
                    try:
                        node_ids.extend(
                            await self.send(
                                cdp.dom.query_selector_all(cd_node.node_id, selector)
                            )
                        )
                    except Exception as e:
                        print(f"Exception in new content doc ids loop {e}")
''', '''            for cd_node in content_doc_nodes:
                # a stale iframe document is retried below like the main document
                node_ids.extend(
                    await self.send(
                        cdp.dom.query_selector_all(cd_node.node_id, selector)
                    )
                )
''')

# find_elements_by_text: return_enclosing_element, tag_hint, dedup
rep('''        text: str,
        tag_hint: Optional[str] = None,
    ) -> list[Element]:''', '''        text: str,
        tag_hint: Optional[str] = None,
        return_enclosing_element: bool = True,
    ) -> list[Element]:''')
rep('''        :param tag_hint: when provided, narrows down search to only elements which match given tag eg: a, div, script, span
        :return:''', '''        :param tag_hint: when provided, narrows down search to only elements which match given tag eg: a, div, script, span
        :param return_enclosing_element: when True (default), text nodes are replaced by the element containing them
        :return:''')
rep('''            if elem.node_type == 3:
                # if found element''', '''            if elem.node_type == 3 and return_enclosing_element:
                # if found element''')
rep('''                    if iframe_text_nodes:
                        iframe_text_elems = [
                            element.create(
                                text_node.node
                                if isinstance(text_node, element.Element)
                                else text_node,
                                self,
                                iframe_elem.tree,
                            )
                            for text_node in iframe_text_nodes
                        ]
                        items.extend(
                            text_node.parent
                            for text_node in iframe_text_elems
                            if text_node.parent
                        )
        await self.disable_dom_agent()
        return items or []''', '''                    if iframe_text_nodes:
                        iframe_text_elems = [
                            element.create(
                                text_node.node
                                if isinstance(text_node, element.Element)
                                else text_node,
                                self,
                                iframe_elem.tree,
                            )
                            for text_node in iframe_text_nodes
                        ]
                        if not return_enclosing_element:
                            items.extend(iframe_text_elems)
                            continue
                        items.extend(
                            text_node.parent
                            for text_node in iframe_text_elems
                            if text_node.parent
                        )
        await self.disable_dom_agent()
        # an element can match more than once (attribute and text, several text nodes)
        unique: dict[cdp.dom.BackendNodeId, Element] = {}
        for item in items:
            unique.setdefault(item.backend_node_id, item)
        items = list(unique.values())
        if tag_hint:
            items = [item for item in items if item.tag == tag_hint.strip().lower()]
        return items''')
rep('''        items = await self.find_elements_by_text(text)
        try:
            if not items:''', '''        items = await self.find_elements_by_text(
            text, return_enclosing_element=bool(return_enclosing_element)
        )
        try:
            if not items:''')
p.write_text(s)
print("patched", p)
