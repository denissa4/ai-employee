from docx import Document
import networkx as nx
import regex as re
from difflib import SequenceMatcher

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


def process_embedded_content(document_path, translations):
    """
    Handles charts, tables, and other embedded objects
    Requires: python-docx
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
