# -*- coding: utf-8 -*-
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals

from markdown import markdown
from mdx_gfm import GithubFlavoredMarkdownExtension
import bleach

def text_to_markdown(text):
    """ This method takes any text and sanitizes it from unsafe html tags.
    Then it converts any markdown syntax into html and returns the result.
    """
    ALLOWED_TAGS = [
        'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'h7', 'h8', 'br', 'b', 'i',
        'strong', 'em', 'a', 'pre', 'code', 'img', 'tt', 'div', 'ins', 'del',
        'sup', 'sub', 'p', 'ol', 'ul', 'table', 'thead', 'tbody', 'tfoot',
        'blockquote', 'dl', 'dt', 'dd', 'kbd', 'q', 'samp', 'var', 'hr', 'ruby',
        'rt', 'rp', 'li', 'tr', 'td', 'th', 's', 'strike', 'summary', 'details'
    ]
    ALLOWED_ATTRIBUTES = {
        '*': [
                'abbr', 'accept', 'accept-charset', 'accesskey', 'action',
                'align', 'alt', 'axis', 'border', 'cellpadding', 'cellspacing',
                'char', 'charoff', 'charset', 'checked', 'clear', 'cols',
                'colspan', 'color', 'compact', 'coords', 'datetime', 'dir',
                'disabled', 'enctype', 'for', 'frame', 'headers', 'height',
                'hreflang', 'hspace', 'ismap', 'label', 'lang', 'maxlength',
                'media', 'method', 'multiple', 'name', 'nohref', 'noshade',
                'nowrap', 'open', 'prompt', 'readonly', 'rel', 'rev', 'rows',
                'rowspan', 'rules', 'scope', 'selected', 'shape', 'size',
                'span', 'start', 'summary', 'tabindex', 'target', 'title',
                'type', 'usemap', 'valign', 'value', 'vspace', 'width',
                'itemprop'
            ],
        'a': ['href'],
        'img': ['src', 'longdesc'],
        'div': ['itemscope', 'itemtype'],
        'blockquote': ['cite'],
        'del': ['cite'],
        'ins': ['cite'],
        'q': ['cite']
    }

    sanitizedText = bleach.clean(text, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRIBUTES)
    markdown_to_safe_html = markdown(sanitizedText,
                             extensions=[GithubFlavoredMarkdownExtension()])
    return markdown_to_safe_html
