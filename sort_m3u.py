import urllib.request
import os

# Khai báo 2 link nguồn
URL_VTV = 'https://github.com/vietng228/m3u/raw/refs/heads/main/m3u.m3u'
URL_OTHER = 'https://tv.vietanhtv.top/tv/'

# Hàm phụ: Tải dữ liệu từ URL
def get_content(url):
    print(f"Đang tải dữ liệu từ {url}...")
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            return response.read().decode('utf-8')
    except Exception as e:
        print(f"Lỗi khi tải file từ {url}: {e}")
        return ""

# Hàm phụ: Cắt dữ liệu thành các Block kênh
def parse_m3u(content):
    lines = content.splitlines(True)
    header_lines = []
    channels = []
    current_block = []
    found_first_channel = False

    for line in lines:
        if line.startswith('#EXTINF'):
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
        
    return header_lines, channels

def download_and_sort_playlist():
    # Tải và bóc tách cả 2 link
    content_vtv = get_content(URL_VTV)
    _, channels_vtv_source = parse_m3u(content_vtv)

    content_other = get_content(URL_OTHER)
    header_lines_other, channels_other_source = parse_m3u(content_other)

    base_filtered_channels = []

    # ==========================================
    # LỌC 1: CHỈ LẤY VTV TỪ LINK GITHUB
    # ==========================================
    for block in channels_vtv_source:
        extinf = block[0].upper()
        if 'GROUP-TITLE="VTV"' in extinf:
            # Vẫn bỏ qua các kênh VTV "độ trễ thấp" bị lỗi
            if 'ĐỘ TRỄ THẤP' in extinf:
                continue
            base_filtered_channels.append(block)

    # ==========================================
    # LỌC 2: LẤY CÁC MỤC KHÁC TỪ LINK VIETANHTV
    # ==========================================
    wanted_others = [
        'GROUP-TITLE="ĐỊA PHƯƠNG"', 'GROUP-TITLE="HTV"',
        'GROUP-TITLE="VTVCAB"', 'GROUP-TITLE="SCTV"', 'GROUP-TITLE="QUỐC TẾ"',
        'GROUP-TITLE="IN THE BOX"'
    ]
    for block in channels_other_source:
        extinf = block[0].upper()
        is_wanted = False
        for group in wanted_others:
            if group in extinf:
                is_wanted = True
                break
        if is_wanted:
            base_filtered_channels.append(block)

    # Hàm chung để sắp xếp độ ưu tiên
    def get_priority(block):
        extinf = block[0].upper()
        if 'GROUP-TITLE="VTV"' in extinf: return 0
        elif 'GROUP-TITLE="ĐỊA PHƯƠNG"' in extinf: return 1
        elif 'GROUP-TITLE="HTV"' in extinf: return 2
        elif 'GROUP-TITLE="VTVCAB"' in extinf: return 3
        elif 'GROUP-TITLE="SCTV"' in extinf: return 4
        elif 'GROUP-TITLE="QUỐC TẾ"' in extinf: return 5
        elif 'GROUP-TITLE="IN THE BOX"' in extinf: return 6
        else: return 7

    # ==========================================
    # TẠO FILE `vtv.m3u` (CHỈ LẤY ĐUÔI .m3u8)
    # ==========================================
    filtered_channels_vtv = []
    for block in base_filtered_channels:
        is_m3u8 = False
        for line in block:
            line_clean = line.strip().lower()
            if not line_clean.startswith('#') and line_clean.startswith('http'):
                link_base = line_clean.split('?')[0]
                if link_base.endswith('.m3u8'):
                    is_m3u8 = True
                break
        if is_m3u8:
            filtered_channels_vtv.append(block)

    filtered_channels_vtv.sort(key=get_priority)

    # Lấy header gốc (thường là #EXTM3U) để ghi vào đầu file
    header_to_write = header_lines_other if header_lines_other else ["#EXTM3U\n"]

    with open('vtv.m3u', 'w', encoding='utf-8') as f:
        f.writelines(header_to_write)
        for block in filtered_channels_vtv:
            f.writelines(block)
    print(f"-> Đã tạo file vtv.m3u (Gồm {len(filtered_channels_vtv)} kênh - CHỈ ĐUÔI .m3u8).")

    # ==========================================
    # TẠO FILE `playlist.m3u` (LẤY TẤT CẢ ĐỊNH DẠNG LINK)
    # ==========================================
    filtered_channels_playlist = base_filtered_channels.copy()
    filtered_channels_playlist.sort(key=get_priority)

    with open('playlist.m3u', 'w', encoding='utf-8') as f:
        f.writelines(header_to_write)
        for block in filtered_channels_playlist:
            f.writelines(block)
    print(f"-> Đã tạo file playlist.m3u (Gồm {len(filtered_channels_playlist)} kênh - TẤT CẢ ĐỊNH DẠNG LINK).")

if __name__ == '__main__':
    download_and_sort_playlist()
