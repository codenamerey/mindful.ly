import base64
import json
import mimetypes
import re
from pathlib import Path


class CodexGateway:
    def __init__(self, *, client_factory, upload_dir, tool_runner, tools):
        self.client_factory = client_factory
        self.upload_dir = upload_dir
        self.tool_runner = tool_runner
        self.tools = tools

    def image_inputs(self, message):
        content = [{"type": "input_text", "text": message}]
        root = Path(self.upload_dir()).resolve()
        seen = set()
        for raw in re.findall(r"(?:/[^\s;,]+\.(?:png|jpe?g|gif|webp|bmp))", message, re.I):
            candidate = Path(raw.rstrip(".)]}\"'"))
            try:
                path = candidate.resolve(strict=True)
            except OSError:
                continue
            if path in seen or root not in path.parents:
                continue
            seen.add(path)
            media_type = mimetypes.guess_type(path.name)[0] or "image/png"
            encoded = base64.b64encode(path.read_bytes()).decode()
            content.append({"type": "input_image", "image_url": f"data:{media_type};base64,{encoded}", "detail": "high"})
        return [{"role": "user", "content": content}]

    def call(self, message, *, timeout_ms=300000, max_tool_turns=64):
        client = self.client_factory(timeout_seconds=(timeout_ms / 1000) + 10)
        result = ""
        try:
            conversation = self.image_inputs(message)
            for _ in range(max_tool_turns + 1):
                response = client.responses.create(input=conversation, tools=self.tools, timeout=(timeout_ms / 1000) + 10)
                if not response.tool_calls:
                    result = response.output_text
                    break
                conversation.extend(response.output)
                for call in response.tool_calls:
                    try:
                        output = self.tool_runner(call.get("name", ""), json.loads(call.get("arguments") or "{}"))
                    except Exception as error:
                        output = {"error": str(error)}
                    conversation.append({"type": "function_call_output", "call_id": call["call_id"], "output": json.dumps(output)})
            else:
                raise RuntimeError("Codex exceeded the tool continuation limit")
        finally:
            client.close()
        if not str(result).strip():
            raise RuntimeError("Codex returned an empty response")
        return result
