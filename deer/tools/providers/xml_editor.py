from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from lxml import etree

from deer.tools import ToolProvider, tool
from deer.tools.schemas import Case, Return


@dataclass
class XMLEditor(ToolProvider):
    """Provides surgical editing and introspection for XML files using XPath."""

    def _get_root(self, safe_path: Path) -> etree._ElementTree:
        # No recover=True: malformed XML must fail instead of being silently "fixed".
        # resolve_entities=False / no_network=True: protection against XXE.
        parser = etree.XMLParser(resolve_entities=False, no_network=True)
        return etree.parse(str(safe_path), parser)

    def _save_tree(self, tree: etree._ElementTree, safe_path: Path) -> None:
        tree.write(
            str(safe_path), encoding="utf-8", xml_declaration=True, pretty_print=True
        )

    @tool(
        tests=[
            Case(
                {"path": "a.xml"},  # full file
                {"results": ["<a><b>1</b></a>"], "message": "Success"},
                files={"a.xml": "<a><b>1</b></a>"},
            ),
            Case(
                {"path": "a.xml", "xpath": "//b"},  # elements
                {"results": ["<b>1</b>", "<b>2</b>"], "message": "Success"},
                files={"a.xml": "<a><b>1</b><b>2</b></a>"},
            ),
            Case(
                {"path": "a.xml", "xpath": "//b/@id"},  # attributes
                {"results": ["1", "2"], "message": "Success"},
                files={"a.xml": '<a><b id="1"/><b id="2"/></a>'},
            ),
            Case(
                {"path": "a.xml", "xpath": "//b/text()"},  # text nodes
                {"results": ["x"], "message": "Success"},
                files={"a.xml": "<a><b>x</b></a>"},
            ),
            Case(
                {"path": "a.xml", "xpath": "//b[@id='2']"},  # predicate
                {"results": ['<b id="2">y</b>'], "message": "Success"},
                files={"a.xml": '<a><b id="1">x</b><b id="2">y</b></a>'},
            ),
            Case(
                {"path": "a.xml", "xpath": "//zzz"},  # no match is not an error
                {"results": [], "message": "Success"},
                files={"a.xml": "<a/>"},
            ),
            Case(
                {"path": "a.xml", "xpath": "//["},  # invalid XPath
                {"results": [], "message": str},
                files={"a.xml": "<a/>"},
            ),
            Case(
                {"path": "a.xml"},  # not XML at all
                {"results": [], "message": str},
                files={"a.xml": "not xml"},
            ),
            Case(
                {"path": "a.xml"},  # malformed XML
                {"results": [], "message": str},
                files={"a.xml": "<a><b>1</a>"},
            ),
            Case(
                {"path": "no_exists.xml"},  # non-existent file
                {"results": [], "message": str},
            ),
            Case({"path": "../outside.xml"}, raises=Exception),  # jail
        ]
    )
    def read_xml(
        self, path: str, xpath: Optional[str] = None
    ) -> Return(results=List[str], message=str):
        """Executes an XPath query against an XML file and returns a list of matching nodes as string representations."""
        safe_path = self.jailed_path(path)
        try:
            tree = self._get_root(safe_path)
            if not xpath:
                return {
                    "results": [etree.tostring(tree, encoding="unicode")],
                    "message": "Success",
                }

            results = []
            for node in tree.xpath(xpath):
                if isinstance(node, etree._Element):
                    results.append(etree.tostring(node, encoding="unicode").strip())
                else:
                    results.append(str(node))

            return {"results": results, "message": "Success"}
        except Exception as e:
            return {"results": [], "message": f"Error: {e}"}

    @tool(
        modifies_state=True,
        tests=[
            Case(
                {"path": "a.xml", "xpath": "/a/b", "value": "2"},  # update text
                {"success": True, "message": str},
                files={"a.xml": "<a><b>1</b></a>"},
                expected_contains={"a.xml": ["<b>2</b>"]},
                expected_absent={"a.xml": ["<b>1</b>"]},
            ),
            Case(
                {
                    "path": "a.xml",
                    "xpath": "/a/b",
                    "attribute": "id",
                    "value": "2",
                },  # update attribute
                {"success": True, "message": str},
                files={"a.xml": '<a><b id="1"/></a>'},
                expected_contains={"a.xml": ['id="2"']},
                expected_absent={"a.xml": ['id="1"']},
            ),
            Case(
                {
                    "path": "a.xml",
                    "xpath": "/a/b",
                    "attribute": "new",
                    "value": "v",
                },  # attribute created
                {"success": True, "message": str},
                files={"a.xml": "<a><b/></a>"},
                expected_contains={"a.xml": ['new="v"']},
            ),
            Case(
                {"path": "a.xml", "xpath": "//b", "value": "9"},  # several nodes
                {"success": True, "message": "Updated 2 nodes matching //b"},
                files={"a.xml": "<a><b>1</b><b>2</b></a>"},
                expected_contains={"a.xml": ["<b>9</b>"]},
                expected_absent={"a.xml": ["<b>1</b>", "<b>2</b>"]},
            ),
            Case(
                {
                    "path": "a.xml",
                    "xpath": "/a/b",
                    "value": "x < y & z",
                },  # special characters are escaped
                {"success": True, "message": str},
                files={"a.xml": "<a><b/></a>"},
                expected_contains={"a.xml": ["x &lt; y &amp; z"]},
            ),
            Case(
                {"path": "a.xml", "xpath": "/a/zzz", "value": "2"},  # no match
                {"success": False, "message": str},
                files={"a.xml": "<a><b>1</b></a>"},
                expected_contains={"a.xml": ["<b>1</b>"]},
            ),
            Case(
                {"path": "a.xml", "xpath": "//b/text()", "value": "2"},  # non-element
                {"success": False, "message": str},
                files={"a.xml": "<a><b>1</b></a>"},
                expected_contains={"a.xml": ["<b>1</b>"]},
            ),
            Case(
                {"path": "a.xml", "xpath": "/a/b", "attribute": "id"},  # no value
                {"success": False, "message": str},
                files={"a.xml": "<a><b>1</b></a>"},
                expected_contains={"a.xml": ["<b>1</b>"]},
            ),
            Case(
                {"path": "a.xml", "xpath": "/a", "value": "2"},  # not XML
                {"success": False, "message": str},
                files={"a.xml": "not xml"},
            ),
            Case(
                {"path": "no_exists.xml", "xpath": "/a", "value": "2"},  # no file
                {"success": False, "message": str},
            ),
            Case(
                {"path": "../outside.xml", "xpath": "/a", "value": "2"},  # jail
                raises=Exception,
            ),
        ],
    )
    def update_xml(
        self,
        path: str,
        xpath: str,
        value: Optional[str] = None,
        attribute: Optional[str] = None,
    ) -> Return(success=bool, message=str):
        """Updates the text, or the given attribute, of every element matching an XPath expression. The XPath must match elements (not text or attribute nodes). Fails if nothing matches."""
        safe_path = self.jailed_path(path)
        try:
            tree = self._get_root(safe_path)
            elements = [n for n in tree.xpath(xpath) if isinstance(n, etree._Element)]

            if not elements:
                return {
                    "success": False,
                    "message": f"XPath must match at least one element: {xpath}",
                }

            for node in elements:
                if attribute:
                    node.set(attribute, value)
                else:
                    node.text = value

            self._save_tree(tree, safe_path)
            return {
                "success": True,
                "message": f"Updated {len(elements)} nodes matching {xpath}",
            }
        except Exception as e:
            return {"success": False, "message": f"Error: {e}"}

    @tool(
        modifies_state=True,
        tests=[
            Case(
                {"path": "a.xml", "parent_xpath": "/a", "tag": "b", "content": "x"},
                {"success": True, "message": str},  # with content
                files={"a.xml": "<a/>"},
                expected_contains={"a.xml": ["<b>x</b>"]},
            ),
            Case(
                {"path": "a.xml", "parent_xpath": "/a", "tag": "b"},  # empty node
                {"success": True, "message": str},
                files={"a.xml": "<a/>"},
                expected_contains={"a.xml": ["<b/>"]},
            ),
            Case(
                {
                    "path": "a.xml",
                    "parent_xpath": "/a",
                    "tag": "b",
                    "attributes": {"id": 1, "k": "v"},
                },  # attributes, values cast to str
                {"success": True, "message": str},
                files={"a.xml": "<a/>"},
                expected_contains={"a.xml": ['id="1"', 'k="v"']},
            ),
            Case(
                {"path": "a.xml", "parent_xpath": "//a", "tag": "b"},  # several parents
                {"success": True, "message": "Added node <b> to 2 parents"},
                files={"a.xml": "<r><a/><a/></r>"},
            ),
            Case(
                {
                    "path": "a.xml",
                    "parent_xpath": "/a",
                    "tag": "b",
                    "content": "x < y",
                },  # special characters
                {"success": True, "message": str},
                files={"a.xml": "<a/>"},
                expected_contains={"a.xml": ["x &lt; y"]},
            ),
            Case(
                {"path": "a.xml", "parent_xpath": "/zzz", "tag": "b"},  # no parent
                {"success": False, "message": str},
                files={"a.xml": "<a/>"},
                expected_absent={"a.xml": ["<b"]},
            ),
            Case(
                {"path": "a.xml", "parent_xpath": "/a", "tag": "1bad"},  # invalid tag
                {"success": False, "message": str},
                files={"a.xml": "<a/>"},
                expected_absent={"a.xml": ["1bad"]},
            ),
            Case(
                {"path": "no_exists.xml", "parent_xpath": "/a", "tag": "b"},
                {"success": False, "message": str},  # non-existent file
            ),
            Case(
                {"path": "../outside.xml", "parent_xpath": "/a", "tag": "b"},
                raises=Exception,  # jail
            ),
        ],
    )
    def add_xml_node(
        self,
        path: str,
        parent_xpath: str,
        tag: str,
        content: Optional[str] = None,
        attributes: Optional[dict] = None,
    ) -> Return(success=bool, message=str):
        """Adds a new child node, with optional text content and attributes, to every element matching the parent XPath. Fails if no element matches."""
        safe_path = self.jailed_path(path)
        try:
            tree = self._get_root(safe_path)
            parents = [
                n for n in tree.xpath(parent_xpath) if isinstance(n, etree._Element)
            ]

            if not parents:
                return {
                    "success": False,
                    "message": f"No parent elements match XPath: {parent_xpath}",
                }

            for parent in parents:
                child = etree.SubElement(parent, tag)
                if content:
                    child.text = content
                if attributes:
                    for k, v in attributes.items():
                        child.set(k, str(v))

            self._save_tree(tree, safe_path)
            return {
                "success": True,
                "message": f"Added node <{tag}> to {len(parents)} parents",
            }
        except Exception as e:
            return {"success": False, "message": f"Error: {e}"}

    @tool(
        modifies_state=True,
        tests=[
            Case(
                {"path": "a.xml", "xpath": "/a/b"},  # remove one node
                {"success": True, "message": str},
                files={"a.xml": "<a><b/><c/></a>"},
                expected_contains={"a.xml": ["<c/>"]},
                expected_absent={"a.xml": ["<b/>"]},
            ),
            Case(
                {"path": "a.xml", "xpath": "//b"},  # several nodes
                {"success": True, "message": "Removed 2 nodes matching //b"},
                files={"a.xml": "<a><b/><b/><c/></a>"},
                expected_contains={"a.xml": ["<c/>"]},
                expected_absent={"a.xml": ["<b/>"]},
            ),
            Case(
                {"path": "a.xml", "xpath": "/a/b"},  # children go with the node
                {"success": True, "message": str},
                files={"a.xml": "<a><b><x/></b><c/></a>"},
                expected_contains={"a.xml": ["<c/>"]},
                expected_absent={"a.xml": ["<x/>"]},
            ),
            Case(
                {"path": "a.xml", "xpath": "/a/zzz"},  # no match: file untouched
                {"success": False, "message": str},
                files={"a.xml": "<a><b/></a>"},
                expected_contains={"a.xml": ["<b/>"]},
            ),
            Case(
                {"path": "a.xml", "xpath": "//b/@id"},  # attributes can't be removed
                {"success": False, "message": str},
                files={"a.xml": '<a><b id="1"/></a>'},
                expected_contains={"a.xml": ['id="1"']},
            ),
            Case(
                {"path": "a.xml", "xpath": "/a"},  # root can't be removed
                {"success": False, "message": str},
                files={"a.xml": "<a><b/></a>"},
                expected_contains={"a.xml": ["<b/>"]},
            ),
            Case(
                {"path": "a.xml", "xpath": "/a/b"},  # not XML
                {"success": False, "message": str},
                files={"a.xml": "not xml"},
            ),
            Case(
                {"path": "no_exists.xml", "xpath": "/a"},  # non-existent file
                {"success": False, "message": str},
            ),
            Case({"path": "../outside.xml", "xpath": "/a"}, raises=Exception),  # jail
        ],
    )
    def remove_xml_node(
        self, path: str, xpath: str
    ) -> Return(success=bool, message=str):
        """Deletes every element matching an XPath expression, together with its children. The XPath must match elements (not attributes or text), and the root element cannot be removed. Fails if nothing matches."""
        safe_path = self.jailed_path(path)
        try:
            tree = self._get_root(safe_path)
            nodes = tree.xpath(xpath)

            if not nodes:
                return {"success": False, "message": f"No nodes match XPath: {xpath}"}

            elements = [n for n in nodes if isinstance(n, etree._Element)]
            if len(elements) != len(nodes):
                return {
                    "success": False,
                    "message": "Cannot remove attributes or text directly via XPath. Target the parent element.",
                }

            if any(node.getparent() is None for node in elements):
                return {"success": False, "message": "Cannot remove the root element."}

            for node in elements:
                node.getparent().remove(node)

            self._save_tree(tree, safe_path)
            return {
                "success": True,
                "message": f"Removed {len(elements)} nodes matching {xpath}",
            }
        except Exception as e:
            return {"success": False, "message": f"Error: {e}"}
