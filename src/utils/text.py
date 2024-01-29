import re as _re


# ----- CONSTANTS -----

RX_HTML_TAG_BOLD: _re.Pattern = _re.compile('</?b>')
RX_HTML_TAG_COLOR: _re.Pattern = _re.compile('</?color.*?>')
RX_HTML_TAG_ITALIC: _re.Pattern = _re.compile('</?i>')
RX_HTML_TAG_SIZE: _re.Pattern = _re.compile('</?size.*?>')


# ----- FUNCTIONS -----

def remove_html_tags(s: str) -> str:
    if not s:
        return s
    
    s = RX_HTML_TAG_BOLD.sub('**', s)
    s = RX_HTML_TAG_ITALIC.sub('_', s)
    s = RX_HTML_TAG_COLOR.sub('', s)
    s = RX_HTML_TAG_SIZE.sub('', s)

    return s