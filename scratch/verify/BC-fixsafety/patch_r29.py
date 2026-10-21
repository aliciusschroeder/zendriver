import pathlib, sys
p = pathlib.Path(sys.argv[1]) / "zendriver/core/tab.py"
s = p.read_text()

def rep(old, new):
    global s
    assert s.count(old) == 1, old
    s = s.replace(old, new)

# --- query_selector_all: re-raise unexpected errors for element-scoped queries
rep('''                    setattr(_node, "__last", True)
                    return await self.query_selector_all(
                        selector, _node, _include_frames=_include_frames
                    )
            else:
                if e.message is not None and "could not find node" in e.message.lower():
                    # The document node is stale; refetch and retry once
                    doc = await self.send(cdp.dom.get_document(-1, True))
                    # Prevent double-retry by marking this node as 'last attempt'
                    setattr(doc, "__last", True)
                    return await self.query_selector_all(
                        selector, doc, _include_frames=_include_frames
                    )

                await self.disable_dom_agent()
                raise
        if not node_ids:
            return []
        items = []

        for nid in node_ids:''', '''                    setattr(_node, "__last", True)
                    return await self.query_selector_all(
                        selector, _node, _include_frames=_include_frames
                    )
            else:
                if e.message is not None and "could not find node" in e.message.lower():
                    # The document node is stale; refetch and retry once
                    doc = await self.send(cdp.dom.get_document(-1, True))
                    # Prevent double-retry by marking this node as 'last attempt'
                    setattr(doc, "__last", True)
                    return await self.query_selector_all(
                        selector, doc, _include_frames=_include_frames
                    )

            await self.disable_dom_agent()
            raise
        if not node_ids:
            return []
        items = []
        # results of an element-scoped query belong to that element's document
        tree = doc
        if isinstance(_node, element.Element) and doc is _node and _node.tree:
            tree = _node.tree

        for nid in node_ids:''')
rep('''            if not node:
                continue
            elem = element.create(node, self, doc)
            items.append(elem)''', '''            if not node:
                continue
            if isinstance(node, element.Element):
                node = node.node
            elem = element.create(node, self, tree)
            items.append(elem)''')

# --- query_selector: cross-origin guard, re-raise, tree
rep('''            doc = _node
            if _node.node_name == "IFRAME":
                doc = _node.content_document
        node_id = None''', '''            doc = _node
            if _node.node_name == "IFRAME":
                doc = _node.content_document
                if doc is None:
                    return None  # cross-origin iframes block access to content_document
        node_id = None''')
rep('''                setattr(doc, "__last", True)
                return await self.query_selector(selector, doc)
            else:
                await self.disable_dom_agent()
                raise
        if not node_id:
            return None
        node = util.filter_recurse(doc, lambda n: n.node_id == node_id)
        if not node:
            return None
        return element.create(node, self, doc)''', '''                setattr(doc, "__last", True)
                return await self.query_selector(selector, doc)
            await self.disable_dom_agent()
            raise
        if not node_id:
            return None
        node = util.filter_recurse(doc, lambda n: n.node_id == node_id)
        if not node:
            return None
        if isinstance(node, element.Element):
            node = node.node
        # results of an element-scoped query belong to that element's document
        tree = doc
        if isinstance(_node, element.Element) and doc is _node and _node.tree:
            tree = _node.tree
        return element.create(node, self, tree)''')

# --- find_elements_by_text: shadow roots in iframes come back as raw cdp nodes
rep('''                        iframe_text_elems = [
                            element.create(text_node.node, self, iframe_elem.tree)
                            for text_node in iframe_text_nodes
                        ]''', '''                        iframe_text_elems = [
                            element.create(
                                text_node.node
                                if isinstance(text_node, element.Element)
                                else text_node,
                                self,
                                iframe_elem.tree,
                            )
                            for text_node in iframe_text_nodes
                        ]''')
p.write_text(s)
print("patched", p)
