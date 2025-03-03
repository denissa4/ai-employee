from lxml import etree
from docx import Document
import networkx as nx
import regex as re
from difflib import SequenceMatcher


def process_document_xml(document_path, operation, modifications=None):
    """
    Processes Word document XML structure with style preservation.
    Requires: python-docx, lxml
    """
    doc = Document(document_path)
    nsmap = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}

    if operation == 'extract':
        return {
            'body_xml': etree.tostring(doc._element.body, pretty_print=True, encoding="unicode"),
            'styles_xml': etree.tostring(doc.styles.element, pretty_print=True, encoding="unicode") if hasattr(doc.styles, "element") else None
        }

    elif operation == 'modify' and modifications:
        for mod in modifications:
            NAMESPACES = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
            xpath_query = etree.XPath(mod['xpath'], namespaces=NAMESPACES)
            for p_elem in xpath_query(doc._element):
                # Iterate over each run element inside the paragraph
                for run_elem in p_elem.findall('.//w:r', namespaces=NAMESPACES):
                    # Skip runs that contain drawing/image elements to preserve images
                    if run_elem.find('.//w:drawing', namespaces=NAMESPACES) is not None:
                        continue
                    # Then, iterate over the text elements
                    for t_elem in run_elem.findall('.//w:t', namespaces=NAMESPACES):
                        if t_elem.text and "Appendix" in t_elem.text:
                            t_elem.text = t_elem.text.replace("Appendix", mod['translated_text'])
                    # Optionally, apply style modifications if desired
                    if 'style_attributes' in mod and isinstance(mod['style_attributes'], dict):
                        for key, value in mod['style_attributes'].items():
                            run_elem.set(key, value)

        new_path = document_path.replace('.docx', '_translated.docx')
        doc.save(new_path)
        return new_path



def map_style_dependencies(document_path):
    """
    Analyzes style inheritance relationships and extracts text content.
    Requires: networkx, python-docx
    """
    from docx.shared import Pt
    from docx.styles.style import ParagraphStyle  # Ensure we only process ParagraphStyle

    doc = Document(document_path)
    G = nx.DiGraph()
    text_content = []

    for style in doc.styles:
        G.add_node(style.name)

        # Only ParagraphStyle objects have base_style
        if isinstance(style, ParagraphStyle) and style.base_style:
            G.add_edge(style.base_style.name, style.name)

        # Only ParagraphStyle objects have next_paragraph_style
        if isinstance(style, ParagraphStyle) and style.next_paragraph_style:
            G.add_edge(style.name, style.next_paragraph_style.name)

    # Extract text content with styles
    for para in doc.paragraphs:
        para_text = para.text.strip()
        if para_text:
            text_content.append({
                'text': para_text,
                'style': para.style.name if para.style else 'Unknown',
                'font': getattr(para.style.font, 'name', None),
                'size': para.style.font.size.pt if para.style.font.size else None
            })

    return {
        'style_graph': nx.node_link_data(G, edges="links"),
        'style_properties': {
            style.name: {
                'font': getattr(style, 'font', None) and getattr(style.font, 'name', None),
                'size': getattr(style, 'font', None) and (style.font.size.pt if style.font.size else None),
                'spacing': getattr(style, 'paragraph_format', None) and getattr(style.paragraph_format, 'line_spacing', None)
            } for style in doc.styles if isinstance(style, ParagraphStyle)  # Filter only ParagraphStyle
        },
        'text_content': text_content
    }


def structured_document_replace(document_path, replacements):
    """
    Performs context-sensitive text replacement by editing the underlying XML.
    This approach modifies only the <w:t> (text) nodes in runs that do not contain
    drawings, so that images and other non-text content are preserved.
    
    If a suffix is provided, a regex is used to replace text between the prefix and suffix.
    If no suffix is provided, an exact match on the text node is performed.
    
    Requires: python-docx, regex, lxml
    """
    doc = Document(document_path)
    NAMESPACES = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}

    for replacement in replacements:
        context = replacement['context']
        # Prepare regex pattern if a suffix is provided
        pattern = None
        if context.get('suffix', ''):
            pattern = re.compile(
                rf'({re.escape(context["prefix"])})\s*(.*?)\s*({re.escape(context["suffix"])})',
                re.DOTALL
            )
        # Iterate over paragraphs in the document
        for paragraph in doc.paragraphs:
            # Check if the paragraph style matches the target style.
            # (Adjust this check if you want to apply replacement regardless of style.)
            if paragraph.style and paragraph.style.name == context['style']:
                # Iterate over runs in the paragraph
                for run in paragraph.runs:
                    # Do not process runs that contain drawings (images)
                    if run._element.find('.//w:drawing', namespaces=NAMESPACES) is not None:
                        continue
                    # Now, iterate over each text element (<w:t>) within the run
                    for t_elem in run._element.findall('.//w:t', namespaces=NAMESPACES):
                        if t_elem.text:
                            if pattern:
                                # Use regex substitution if pattern is defined
                                new_text = pattern.sub(rf'\1 {replacement["translated"]} \3', t_elem.text)
                                t_elem.text = new_text
                            else:
                                # No suffix provided: if the entire text exactly matches the prefix, replace it
                                if t_elem.text.strip() == context["prefix"]:
                                    t_elem.text = replacement["translated"]

    new_path = document_path.replace('.docx', '_replaced.docx')
    doc.save(new_path)
    return new_path


def validate_document_integrity(original_path, translated_path):
    """
    Compares document formatting at granular level
    Requires: python-docx, difflib
    """
    orig_doc = Document(original_path)
    trans_doc = Document(translated_path)

    report = {
        'paragraph_alignment': [],
        'style_mismatches': [],
        'layout_diffs': []
    }

    for orig_para, trans_para in zip(orig_doc.paragraphs, trans_doc.paragraphs):
        # Compare formatting properties
        fmt_match = SequenceMatcher(
            None, 
            str(orig_para.paragraph_format), 
            str(trans_para.paragraph_format)
        ).ratio()
        
        report['paragraph_alignment'].append({
            'original_style': orig_para.style.name if hasattr(orig_para.style, 'name') else 'Unknown',
            'translated_style': trans_para.style.name if hasattr(trans_para.style, 'name') else 'Unknown',
            'format_match': fmt_match
        })

    return report


def process_embedded_content(document_path, translations):
    """
    Handles charts, tables, and other embedded objects
    Requires: python-docx, pandas
    """
    doc = Document(document_path)
    
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                if cell.text.strip() in translations:
                    cell.text = translations[cell.text.strip()]
    
    for shape in doc.inline_shapes:
        if hasattr(shape, 'chart'):
            chart_part = shape.chart
            # Translate chart data labels
            for series in chart_part.series:
                if hasattr(series, 'name'):
                    series.name = translations.get(series.name, series.name)
    
    new_path = document_path.replace('.docx', '_embedded.docx')
    doc.save(new_path)
    return new_path
