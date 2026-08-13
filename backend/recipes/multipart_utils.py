"""
Minimal multipart/form-data parser using the stdlib `email` package —
no extra dependency needed. Good enough for a single-file upload field.
"""
import email
from email import policy


def parse_multipart(content_type: str, raw_bytes: bytes) -> dict:
    """Parse a multipart/form-data body into {field_name: {filename, content_type, content}}.

    `content_type` must include the boundary, e.g.
    "multipart/form-data; boundary=----WebKitFormBoundaryXYZ".
    """
    header = f"Content-Type: {content_type}\r\nMIME-Version: 1.0\r\n\r\n".encode()
    msg = email.message_from_bytes(header + raw_bytes, policy=policy.default)

    fields = {}
    if not msg.is_multipart():
        return fields

    for part in msg.iter_parts():
        name = part.get_param("name", header="Content-Disposition")
        if not name:
            continue
        fields[name] = {
            "filename": part.get_filename(),
            "content_type": part.get_content_type(),
            "content": part.get_payload(decode=True),
        }
    return fields