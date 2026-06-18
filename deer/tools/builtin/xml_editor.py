from dataclasses import dataclass
from lxml import etree
from typing import Any, Optional, Union, List
from deer.tools import ToolProvider, tool
from deer.schema.io import Return


@dataclass
class XMLEditor(ToolProvider):
    """Provides surgical editing and introspection for XML files using XPath."""

    def _get_root(self, path: str) -> etree._ElementTree:
        safe_path = self.jailed_path(path)
        parser = etree.XMLParser(remove_blank_text=False, recover=True)
        return etree.parse(str(safe_path), parser)

    def _save_tree(self, tree: etree._ElementTree, path: str):
        safe_path = self.jailed_path(path)
        tree.write(
            str(safe_path), 
            encoding="utf-8", 
            xml_declaration=True, 
            pretty_print=True
        )

    @tool()
    def read_xml(
        self, path: str, xpath: Optional[str] = None
    ) -> Return(results=List[str], message=str):
        """Executes an XPath query against an XML file and returns a list of matching nodes as string representations."""
        try:
            tree = self._get_root(path)
            if not xpath:
                return {"results": [etree.tostring(tree, encoding="unicode")], "message": "Success"}

            nodes = tree.xpath(xpath)
            results = []
            for node in nodes:
                if isinstance(node, etree._Element):
                    results.append(etree.tostring(node, encoding="unicode").strip())
                else:
                    results.append(str(node))
            
            return {"results": results, "message": "Success"}
        except Exception as e:
            return {"results": [], "message": f"Error: {str(e)}"}

    @tool(modifies_state=True)
    def update_xml(
        self, path: str, xpath: str, value: Optional[str] = None, attribute: Optional[str] = None
    ) -> Return(success=bool, message=str):
        """Surgically updates node text or attributes matching an XPath expression, maintaining the XML's structural integrity."""
        try:
            tree = self._get_root(path)
            nodes = tree.xpath(xpath)
            
            if not nodes:
                return {"success": False, "message": f"No nodes match XPath: {xpath}"}

            for node in nodes:
                if not isinstance(node, etree._Element):
                    continue
                
                if attribute:
                    node.set(attribute, value)
                else:
                    node.text = value

            self._save_tree(tree, path)
            return {"success": True, "message": f"Updated {len(nodes)} nodes matching {xpath}"}
        except Exception as e:
            return {"success": False, "message": f"Error: {str(e)}"}

    @tool(modifies_state=True)
    def add_xml_node(
        self, path: str, parent_xpath: str, tag: str, content: Optional[str] = None, attributes: Optional[dict] = None
    ) -> Return(success=bool, message=str):
        """Injects a new child node with optional content and attributes into all elements matching the parent XPath."""
        try:
            tree = self._get_root(path)
            parents = tree.xpath(parent_xpath)
            
            if not parents:
                return {"success": False, "message": f"No parent nodes match XPath: {parent_xpath}"}

            for parent in parents:
                if not isinstance(parent, etree._Element):
                    continue
                
                child = etree.SubElement(parent, tag)
                if content:
                    child.text = content
                if attributes:
                    for k, v in attributes.items():
                        child.set(k, str(v))

            self._save_tree(tree, path)
            return {"success": True, "message": f"Added node <{tag}> to {len(parents)} parents"}
        except Exception as e:
            return {"success": False, "message": f"Error: {str(e)}"}

    @tool(modifies_state=True)
    def remove_xml_node(
        self, path: str, xpath: str
    ) -> Return(success=bool, message=str):
        """Surgically deletes all XML nodes that match a specific XPath expression from the target file."""
        try:
            tree = self._get_root(path)
            nodes = tree.xpath(xpath)
            
            if not nodes:
                return {"success": False, "message": f"No nodes match XPath: {xpath}"}

            for node in nodes:
                if isinstance(node, etree._Element):
                    parent = node.getparent()
                    if parent is not None:
                        parent.remove(node)
                elif isinstance(node, etree._ElementUnicodeResult):
                    # This is likely an attribute or text result, can't "remove" via parent.remove
                    return {"success": False, "message": "Cannot remove attributes or text directly via XPath. Target the parent element."}

            self._save_tree(tree, path)
            return {"success": True, "message": f"Removed {len(nodes)} nodes matching {xpath}"}
        except Exception as e:
            return {"success": False, "message": f"Error: {str(e)}"}
