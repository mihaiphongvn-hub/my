import os
import urllib.request
import urllib.error
from urllib.parse import urlsplit

SOURCE_URL = os.environ.get("SOURCE_URL", "").strip()

def get_content(url):
    print("Đang tải nguồn playlist...")

    if not url:
        raise RuntimeError(
            "Thiếu biến SOURCE_URL. Hãy tạo GitHub Secret SOURCE_URL."
        )

    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0",
                "Accept": "*/*",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache",
            },
        )

        with urllib.request.urlopen(req, timeout=30) as response:
            data = response.read()

        text = data.decode("utf-8", errors="replace")

        if not text.strip():
            raise RuntimeError("Nguồn playlist trả dữ liệu rỗng.")

        if "#EXTM3U" not in text[:1000]:
            raise RuntimeError("Dữ liệu tải về không phải playlist M3U.")

        print(f"[OK] Đã tải {len(data)} bytes.")
        return text

    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"Nguồn trả HTTP {exc.code}.") from None

    except urllib.error.URLError:
        raise RuntimeError("Không kết nối được tới nguồn playlist.") from None


def parse_m3u(content):
    lines = content.splitlines(True)
    header_lines = []
    channels = []
    current_block = []
    found_first_channel = False

    for line in lines:
        if line.startswith("#EXTINF"):
            found_first_channel = True

            if current_block:
                channels.append(current_block)

            current_block = [line]

        elif found_first_channel:
            current_block.append(line)

        else:
            header_lines.append(line)

    if current_block:
        channels.append(current_block)

    if not header_lines:
        header_lines = ["#EXTM3U\n"]

    return header_lines, channels


def get_stream_url(block):
    for line in block:
        line = line.strip()

        if not line or line.startswith("#"):
            continue

        if line.lower().startswith(("http://", "https://")):
            return line

    return ""


def is_m3u8_url(url):
    if not url:
        return False

    base_url = url.split("|", 1)[0]

    try:
        return urlsplit(base_url).path.lower().endswith(".m3u8")
    except Exception:
        return ".m3u8" in base_url.lower()


def get_priority(block):
    extinf = block[0].upper()

    if 'GROUP-TITLE="VTV"' in extinf:
        return 0
    if 'GROUP-TITLE="ĐỊA PHƯƠNG"' in extinf:
        return 1
    if 'GROUP-TITLE="HTV"' in extinf:
        return 2
    if 'GROUP-TITLE="VTVCAB"' in extinf:
        return 3
    if 'GROUP-TITLE="SCTV"' in extinf:
        return 4
    if 'GROUP-TITLE="QUỐC TẾ"' in extinf:
        return 5
    if 'GROUP-TITLE="IN THE BOX"' in extinf:
        return 6

    return 99


def main():
    content = get_content(SOURCE_URL)
    header, channels = parse_m3u(content)

    if not channels:
        raise RuntimeError("Playlist không có block #EXTINF nào.")

    selected = []

    wanted_others = [
        'GROUP-TITLE="ĐỊA PHƯƠNG"',
        'GROUP-TITLE="HTV"',
        'GROUP-TITLE="VTVCAB"',
        'GROUP-TITLE="SCTV"',
        'GROUP-TITLE="QUỐC TẾ"',
        'GROUP-TITLE="IN THE BOX"',
    ]

    for block in channels:
        if not block:
            continue

        extinf = block[0].upper()

        if 'GROUP-TITLE="VTV"' in extinf:
            if "ĐỘ TRỄ THẤP" in extinf:
                continue

            selected.append(block)
            continue

        if any(group in extinf for group in wanted_others):
            selected.append(block)

    selected.sort(key=get_priority)

    m3u8_only = [
        block for block in selected
        if is_m3u8_url(get_stream_url(block))
    ]

    with open("vtv.m3u", "w", encoding="utf-8", newline="") as f:
        f.writelines(header)

        for block in m3u8_only:
            f.writelines(block)

    with open("playlist.m3u", "w", encoding="utf-8", newline="") as f:
        f.writelines(header)

        for block in selected:
            f.writelines(block)

    print(f"Playlist nguồn : {len(channels)} kênh")
    print(f"Đã chọn        : {len(selected)} kênh")
    print(f"vtv.m3u        : {len(m3u8_only)} kênh .m3u8")
    print("Hoàn tất.")


if __name__ == "__main__":
    main()
