import urllib.request
import os

# Link chứa file M3U gốc của bạn
URL = 'https://github.com/vietng228/m3u/raw/refs/heads/main/m3u.m3u' 

def download_and_sort_playlist():
    print(f"Đang tải dữ liệu từ {URL}...")
    try:
        req = urllib.request.Request(URL, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            content = response.read().decode('utf-8')
    except Exception as e:
        print(f"Lỗi khi tải file từ link gốc: {e}")
        return

    lines = content.splitlines(True)

    header_lines = []
    channels = []
    current_block = []
    found_first_channel = False

    # Phân tách phần Header và các block Kênh
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

    # Danh sách các nhóm kênh được phép giữ lại cho cả 2 file
    wanted_groups = [
        'GROUP-TITLE="VTV"', 'GROUP-TITLE="ĐỊA PHƯƠNG"', 'GROUP-TITLE="HTV"',
        'GROUP-TITLE="VTVCAB"', 'GROUP-TITLE="SCTV"', 'GROUP-TITLE="QUỐC TẾ"',
        'GROUP-TITLE="IN THE BOX"'
    ]

    # ==========================================
    # BƯỚC CHUNG: LỌC CÁC NHÓM YÊU CẦU & BỎ VTV LỖI ĐỘ TRỄ THẤP
    # ==========================================
    base_filtered_channels = []
    for block in channels:
        extinf = block[0].upper()
        
        # Bỏ qua kênh VTV "độ trễ thấp"
        if 'GROUP-TITLE="VTV"' in extinf and 'ĐỘ TRỄ THẤP' in extinf:
            continue
            
        # Kiểm tra kênh có thuộc danh sách 7 nhóm yêu cầu không
        is_wanted = False
        for group in wanted_groups:
            if group in extinf:
                is_wanted = True
                break
                
        if is_wanted:
            base_filtered_channels.append(block)

    # ==========================================
    # LUỒNG 1: TẠO FILE `vtv.m3u` (CHỈ LẤY ĐUÔI .m3u8)
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

    with open('vtv.m3u', 'w', encoding='utf-8') as f:
        f.writelines(header_lines)
        for block in filtered_channels_vtv:
            f.writelines(block)
    print(f"-> Đã tạo file vtv.m3u (Gồm {len(filtered_channels_vtv)} kênh - CHỈ ĐUÔI .m3u8).")

    # ==========================================
    # LUỒNG 2: TẠO FILE `playlist.m3u` (LẤY TẤT CẢ CÁC ĐỊNH DẠNG LINK)
    # ==========================================
    filtered_channels_playlist = base_filtered_channels.copy()
    filtered_channels_playlist.sort(key=get_priority)

    with open('playlist.m3u', 'w', encoding='utf-8') as f:
        f.writelines(header_lines)
        for block in filtered_channels_playlist:
            f.writelines(block)
    print(f"-> Đã tạo file playlist.m3u (Gồm {len(filtered_channels_playlist)} kênh - TẤT CẢ ĐỊNH DẠNG LINK).")

if __name__ == '__main__':
    download_and_sort_playlist()
