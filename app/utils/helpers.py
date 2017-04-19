# -*- coding: utf-8 -*-
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals

from markdown import markdown
from mdx_gfm import GithubFlavoredMarkdownExtension
import bleach
import re
import json


def text_to_markdown(text):
    """ This method takes any text and sanitizes it from unsafe html tags.
    Then it converts any markdown syntax into html and returns the result.
    """
    ALLOWED_TAGS = [
        'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'h7', 'h8', 'br', 'b', 'i', 'span',
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
                'itemprop', 'class'
            ],
        'a': ['href'],
        'img': ['src', 'longdesc'],
        'div': ['itemscope', 'itemtype'],
        'blockquote': ['cite'],
        'del': ['cite'],
        'ins': ['cite'],
        'q': ['cite']
    }
    markdown_to_html = markdown(text,
                                extensions=[GithubFlavoredMarkdownExtension()])
    sanitized_html = bleach.clean(markdown_to_html,
                                tags=ALLOWED_TAGS,
                                attributes=ALLOWED_ATTRIBUTES)
    return sanitized_html


def dp_in_readme(readme, dp):
    """ This method takes a readme and data package as arguments. If there is dp
    variables in readme, it returns readme with datapackage json embed into it.
    Dp variables must be wrapped in double curly braces and can be one of:
    datapackage.json, datapackage, dp.json, dp.
    """
    regex = "({{ ?)(datapackage(\.json)?|dp(\.json)?)( ?}})"
    dp_copy = dict(dp)
    if 'readme' in dp_copy:
        dp_copy.pop('readme')
    if 'owner' in dp_copy:
        dp_copy.pop('owner')
    dp_as_md = '\n```json\n' + json.dumps(dp_copy, indent=2) + '\n```\n'
    readme_with_dp = re.sub(regex, dp_as_md, readme)
    return readme_with_dp
