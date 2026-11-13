from redbus_automation.html_utils import escape_html


def test_escape_html_blocks_script_injection():
    payload = '<script>alert("xss")</script>'

    escaped = escape_html(payload)

    assert escaped == "&lt;script&gt;alert(&quot;xss&quot;)&lt;/script&gt;"
    assert "<script>" not in escaped
