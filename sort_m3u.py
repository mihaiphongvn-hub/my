import io
import os
import re
import tempfile
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

SOURCE_PLAYLIST_URL = os.environ.get("SOURCE_PLAYLIST_URL", "").strip()

# Repo logo công khai của bạn
LOGO_REPO_OWNER = "mihaiphongvn-hub"
LOGO_REPO_NAME = "logos"
LOGO_BRANCH = "master"

LOGO_ZIP_URL = (
    f"https://codeload.github.com/"
    f"{LOGO_REPO_OWNER}/{LOGO_REPO_NAME}/zip/refs/heads/{LOGO_BRANCH}"
)

RAW_LOGO_BASE = (
    f"https://raw.githubusercontent.com/"
    f"{LOGO_REPO_OWNER}/{LOGO_REPO_NAME}/{LOGO_BRANCH}/"
)

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg", ".avif"}
ATTR_RE = re.compile(r'([A-Za-z0-9_-]+)="([^"]*)"')
TVG_LOGO_RE = re.compile(r'\s+tvg-logo="[^"]*"', re.IGNORECASE)


def fail(message):
    raise RuntimeError(message)


def download(url, label, timeout=60):
    print(f"Đang tải {label}...")

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

        with urllib.request.urlopen(req, timeout=timeout) as response:
            data = response.read()

        if not data:
            fail(f"{label} trả dữ liệu rỗng.")

        print(f"[OK] {label}: {len(data)} bytes.")
        return data

    except urllib.error.HTTPError as exc:
        fail(f"{label} lỗi HTTP {exc.code}.")
    except urllib.error.URLError:
        fail(f"Không kết nối được tới {label}.")


def normalize_name(text):
    text = urllib.parse.unquote(text or "")
    text = text.replace("Đ", "D").replace("đ", "d")
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower().replace("&", "and")
    return re.sub(r"[^a-z0-9]+", "", text)


def relaxed_name(text):
    name = normalize_name(text)

    for suffix in ("fullhd", "fhd", "uhd", "4k", "hd"):
        if name.endswith(suffix) and len(name) > len(suffix) + 2:
            return name[:-len(suffix)]

    return name


def load_logo_index(zip_bytes):
    exact = {}
    relaxed = {}
    basename = {}

    with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue

            path = Path(info.filename)

            if path.suffix.lower() not in IMAGE_EXTS:
                continue

            # Bỏ thư mục gốc do GitHub ZIP tạo, ví dụ logos-master/
            parts = path.parts
            if len(parts) < 2:
                continue

            rel = Path(*parts[1:]).as_posix()
            stem = Path(rel).stem
            filename = Path(rel).name.lower()

            key = normalize_name(stem)
            key_relaxed = relaxed_name(stem)

            if key:
                exact.setdefault(key, rel)

            if key_relaxed:
                relaxed.setdefault(key_relaxed, rel)

            basename.setdefault(filename, rel)

    if not exact:
        fail("Không đọc được logo nào từ repo.")

    print(f"[OK] Đã lập chỉ mục {len(exact)} logo.")
    return exact, relaxed, basename


def parse_m3u(content):
    lines = content.splitlines(True)

    header = []
    channels = []
    current = []
    found = False

    for line in lines:
        if line.startswith("#EXTINF"):
            found = True

            if current:
                channels.append(current)

            current = [line]

        elif found:
            current.append(line)

        else:
            header.append(line)

    if current:
        channels.append(current)

    if not header:
        header = ["#EXTM3U\n"]

    return header, channels


def parse_extinf(line):
    attrs = {k.lower(): v for k, v in ATTR_RE.findall(line)}
    display = line.split(",", 1)[1].strip() if "," in line else ""
    return attrs, display


def old_logo_basename(url):
    if not url:
        return ""

    try:
        path = urllib.parse.urlsplit(url).path
        return Path(urllib.parse.unquote(path)).name.lower()
    except Exception:
        return ""


def choose_logo(line, exact, relaxed, basename):
    attrs, display = parse_extinf(line)

    # Ưu tiên tên file logo cũ nếu repo mới có đúng basename đó.
    old_base = old_logo_basename(attrs.get("tvg-logo", ""))

    if old_base and old_base in basename:
        return basename[old_base]

    candidates = [
        attrs.get("tvg-id", ""),
        attrs.get("tvg-name", ""),
        display,
    ]

    for value in candidates:
        key = normalize_name(value)
        if key and key in exact:
            return exact[key]

    for value in candidates:
        key = relaxed_name(value)
        if key and key in relaxed:
            return relaxed[key]

    return None


def make_logo_url(rel):
    encoded = "/".join(
        urllib.parse.quote(part)
        for part in rel.split("/")
    )

    return RAW_LOGO_BASE + encoded


def replace_logo(line, url):
    newline = "\n" if line.endswith("\n") else ""
    core = line[:-1] if newline else line

    if TVG_LOGO_RE.search(core):
        core = TVG_LOGO_RE.sub(
            f' tvg-logo="{url}"',
            core,
            count=1,
        )
    else:
        comma = core.find(",")

        if comma >= 0:
            core = core[:comma] + f' tvg-logo="{url}"' + core[comma:]
        else:
            core += f' tvg-logo="{url}"'

    return core + newline


def get_stream_url(block):
    for line in block:
        value = line.strip()

        if not value or value.startswith("#"):
            continue

        if value.lower().startswith(("http://", "https://")):
            return value

    return ""


def is_m3u8(url):
    if not url:
        return False

    base = url.split("|", 1)[0]

    try:
        return urllib.parse.urlsplit(base).path.lower().endswith(".m3u8")
    except Exception:
        return ".m3u8" in base.lower()


def priority(block):
    ext = block[0].upper()

    groups = (
        'GROUP-TITLE="VTV"',
        'GROUP-TITLE="ĐỊA PHƯƠNG"',
        'GROUP-TITLE="HTV"',
        'GROUP-TITLE="VTVCAB"',
        'GROUP-TITLE="SCTV"',
        'GROUP-TITLE="QUỐC TẾ"',
        'GROUP-TITLE="IN THE BOX"',
    )

    for i, group in enumerate(groups):
        if group in ext:
            return i

    return 99


def wanted_channel(block):
    if not block:
        return False

    ext = block[0].upper()

    if 'GROUP-TITLE="VTV"' in ext:
        return "ĐỘ TRỄ THẤP" not in ext

    wanted = (
        'GROUP-TITLE="ĐỊA PHƯƠNG"',
        'GROUP-TITLE="HTV"',
        'GROUP-TITLE="VTVCAB"',
        'GROUP-TITLE="SCTV"',
        'GROUP-TITLE="QUỐC TẾ"',
        'GROUP-TITLE="IN THE BOX"',
    )

    return any(group in ext for group in wanted)


def write_playlist(path, header, blocks):
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.writelines(header)

        for block in blocks:
            f.writelines(block)


def main():
    if not SOURCE_PLAYLIST_URL:
        fail("Thiếu GitHub Secret SOURCE_PLAYLIST_URL.")

    playlist_bytes = download(
        SOURCE_PLAYLIST_URL,
        "playlist nguồn",
        timeout=45,
    )

    logo_zip = download(
        LOGO_ZIP_URL,
        "kho logo GitHub",
        timeout=90,
    )

    try:
        playlist_text = playlist_bytes.decode("utf-8")
    except UnicodeDecodeError:
        playlist_text = playlist_bytes.decode("utf-8", errors="replace")

    if "#EXTM3U" not in playlist_text[:1000]:
        fail("Dữ liệu playlist nguồn không phải M3U.")

    exact, relaxed, basename = load_logo_index(logo_zip)

    header, channels = parse_m3u(playlist_text)

    selected = [
        block for block in channels
        if wanted_channel(block)
    ]

    selected.sort(key=priority)

    matched = 0
    not_matched = []

    for block in selected:
        if not block:
            continue

        rel = choose_logo(
            block[0],
            exact,
            relaxed,
            basename,
        )

        if rel:
            block[0] = replace_logo(
                block[0],
                make_logo_url(rel),
            )
            matched += 1
        else:
            _, display = parse_extinf(block[0])
            not_matched.append(display)

    m3u8_only = [
        block for block in selected
        if is_m3u8(get_stream_url(block))
    ]

    write_playlist("playlist.m3u", header, selected)
    write_playlist("vtv.m3u", header, m3u8_only)

    print()
    print(f"Kênh nguồn          : {len(channels)}")
    print(f"Kênh đã chọn        : {len(selected)}")
    print(f"Kênh gắn được logo : {matched}")
    print(f"Kênh chưa có logo  : {len(not_matched)}")
    print(f"vtv.m3u             : {len(m3u8_only)}")

    if not_matched:
        print("\nMột số kênh chưa match logo:")
        for name in not_matched[:30]:
            print(" -", name)

    print()
    print("Logo sử dụng trực tiếp từ repo mihaiphongvn-hub/logos.")


if __name__ == "__main__":
    main()
