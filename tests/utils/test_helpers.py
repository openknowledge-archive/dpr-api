# -*- coding: utf-8 -*-
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals

from app.utils.helpers import text_to_markdown
import unittest

class HelpersTestCase(unittest.TestCase):
    def test_allowed_tags_working(self):
        self.assertEqual(text_to_markdown("<h1>test</h1>"), "<h1>test</h1>")

    def test_disallowed_tags(self):
        self.assertEqual(text_to_markdown("<script>test</script>"),
                         "&lt;script&gt;test&lt;/script&gt;")

    def test_allowed_attr_working(self):
        self.assertEqual(text_to_markdown(
                "<a href='https://example.com'>test</a>"
            ),
            '<p><a href="https://example.com">test</a></p>')

    def test_blockquotes_working(self):
        self.assertEqual(text_to_markdown("> this is a blockquote"),
            '<blockquote>\n<p>this is a blockquote</p>\n</blockquote>')
