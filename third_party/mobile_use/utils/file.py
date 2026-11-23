# Copyright 2025-2026 Minitap, Inc.
# Modifications Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Originally from mobile-use (https://github.com/minitap-ai/mobile-use).
# See third_party/mobile_use/METADATA for the upstream source and local modifications.

import json
import re
from typing import IO


def strip_json_comments(text: str) -> str:
    """Strip // and /* */ comments, but never inside a JSON string literal.

    Local fix: upstream used a regex that also ate "//" inside values such as
    http URLs, leaving unparseable JSON.
    """
    out = []
    i = 0
    n = len(text)
    in_str = False
    DQ = chr(34)
    BS = chr(92)
    while i < n:
        ch = text[i]
        if in_str:
            out.append(ch)
            if ch == BS and i + 1 < n:
                out.append(text[i + 1])
                i += 2
                continue
            if ch == DQ:
                in_str = False
            i += 1
            continue
        if ch == DQ:
            in_str = True
            out.append(ch)
            i += 1
            continue
        if ch == "/" and i + 1 < n and text[i + 1] == "/":
            while i < n and text[i] != chr(10):
                i += 1
            continue
        if ch == "/" and i + 1 < n and text[i + 1] == "*":
            i += 2
            while i + 1 < n and not (text[i] == "*" and text[i + 1] == "/"):
                i += 1
            i += 2
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def load_jsonc(file: IO) -> dict:
    return json.loads(strip_json_comments(file.read()))
