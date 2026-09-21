import os
import urllib.request
import urllib.error
from urllib.parse import urlsplit


# =========================================================

URL_VTV = os.environ.get("URL_VTV", "").strip()
URL_OTHER = os.environ.get("URL_OTHER", "").strip()


def require_sources():
    if not URL_VTV:
        raise RuntimeError("Thiếu GitHub Secret: URL_VTV")
    if not URL_OTHER:
        raise RuntimeError("Thiếu GitHub Secret: URL_OTHER")


# =========================================================

def get_content(url, source_name):
    print(f"Đang tải {source_name}...")

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
            print(f"[LỖI] {source_name} trả dữ liệu rỗng.")
            return ""

        if "#EXTM3U" not in text[:1000]:
            print(f"[LỖI] {source_name} không giống playlist M3U.")
            return ""

        print(f"[OK] {source_name}: {len(data)} bytes.")
        return text

    except urllib.error.HTTPError as exc:
        # Chỉ hiện HTTP status, không hiện URL.
        print(f"[LỖI] {source_name}: HTTP {exc.code}.")
        return ""

    except urllib.error.URLError:
        print(f"[LỖI] {source_name}: không kết nối được.")
        return ""

    except Exception:
        print(f"[LỖI] {source_name}: tải dữ liệu thất bại.")
        return ""


# =========================================================
# PARSE PLAYLIST THÀNH TỪNG BLOCK KÊNH
# =========================================================

def parse_m3u(content):
    if not content:
        return ["#EXTM3U\n"], []

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


# =========================================================
# LẤY STREAM URL TRONG BLOCK
# =========================================================

def get_stream_url(block):
    for line in block:
        line = line.strip()

        if not line or line.startswith("#"):
            continue

        if line.lower().startswith(("http://", "https://")):
            return line

    return ""


# =========================================================
# KIỂM TRA URL CÓ PHẢI .M3U8
# Hỗ trợ:
#   link.m3u8?token=...
#   link.m3u8|User-Agent=...
# =========================================================

def is_m3u8_url(url):
    if not url:
        return False

    base_url = url.split("|", 1)[0]

    try:
        return urlsplit(base_url).path.lower().endswith(".m3u8")
    except Exception:
        return ".m3u8" in base_url.lower()


# =========================================================
# ĐỘ ƯU TIÊN NHÓM
# =========================================================

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


# =========================================================
# MAIN
# =========================================================

def download_and_sort_playlist():
    require_sources()

    print("=" * 60)
    print("AUTO FETCH AND SORT M3U")
    print("=" * 60)

    # -----------------------------------------------------
    # NGUỒN VTV
    # -----------------------------------------------------

    content_vtv = get_content(URL_VTV, "nguồn VTV")
    header_vtv, channels_vtv_source = parse_m3u(content_vtv)

    if not channels_vtv_source:
        raise RuntimeError("Không lấy được kênh từ nguồn VTV.")

    # -----------------------------------------------------
    # NGUỒN CÁC NHÓM KHÁC
    # -----------------------------------------------------

    content_other = get_content(URL_OTHER, "nguồn OTHER")
    header_other, channels_other_source = parse_m3u(content_other)

    if not channels_other_source:
        raise RuntimeError("Không lấy được kênh từ nguồn OTHER.")

    base_filtered_channels = []

    # =====================================================
    # VTV
    # =====================================================

    vtv_count = 0

    for block in channels_vtv_source:
        if not block:
            continue

        extinf = block[0].upper()

        if 'GROUP-TITLE="VTV"' in extinf:
            if "ĐỘ TRỄ THẤP" in extinf:
                continue

            base_filtered_channels.append(block)
            vtv_count += 1

    # =====================================================
    # NHÓM KHÁC
    # =====================================================

    wanted_others = [
        'GROUP-TITLE="ĐỊA PHƯƠNG"',
        'GROUP-TITLE="HTV"',
        'GROUP-TITLE="VTVCAB"',
        'GROUP-TITLE="SCTV"',
        'GROUP-TITLE="QUỐC TẾ"',
        'GROUP-TITLE="IN THE BOX"',
    ]

    other_count = 0

    for block in channels_other_source:
        if not block:
            continue

        extinf = block[0].upper()

        if any(group in extinf for group in wanted_others):
            base_filtered_channels.append(block)
            other_count += 1

    # =====================================================
    # HEADER
    # =====================================================

    header_to_write = header_other or header_vtv or ["#EXTM3U\n"]

    # =====================================================
    # vtv.m3u
    # CHỈ LINK .m3u8
    # =====================================================

    filtered_m3u8 = []

    for block in base_filtered_channels:
        stream_url = get_stream_url(block)

        if is_m3u8_url(stream_url):
            filtered_m3u8.append(block)

    filtered_m3u8.sort(key=get_priority)

    with open("vtv.m3u", "w", encoding="utf-8", newline="") as f:
        f.writelines(header_to_write)

        for block in filtered_m3u8:
            f.writelines(block)

    # =====================================================
    # playlist.m3u
    # TẤT CẢ STREAM
    # =====================================================

    playlist_channels = base_filtered_channels.copy()
    playlist_channels.sort(key=get_priority)

    with open("playlist.m3u", "w", encoding="utf-8", newline="") as f:
        f.writelines(header_to_write)

        for block in playlist_channels:
            f.writelines(block)

    print()
    print(f"VTV đã chọn          : {vtv_count}")
    print(f"Nhóm khác đã chọn    : {other_count}")
    print(f"vtv.m3u (.m3u8)      : {len(filtered_m3u8)} kênh")
    print(f"playlist.m3u (tất cả): {len(playlist_channels)} kênh")
    print("Hoàn tất. URL nguồn không được ghi vào log.")


if __name__ == "__main__":
    download_and_sort_playlist()
