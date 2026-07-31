import urllib.request
import os

# Link chứa file M3U gốc của bạn
URL = 'https://tv.vietanhtv.top/tv/' 
# Tên file bạn muốn lưu trên GitHub
FILE_PATH = 'vtv.m3u'

def download_and_sort_playlist():
    print(f"Đang tải dữ liệu từ {URL}...")
    try:
        # Thêm Header User-Agent để tránh bị máy chủ chặn
        req = urllib.request.Request(URL, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            content = response.read().decode('utf-8')
    except Exception as e:
        print(f"Lỗi khi tải file từ link gốc: {e}")
        return

    # Tách dữ liệu thành từng dòng
    lines = content.splitlines(True)

    header_lines = []
    channels = []
    current_block = []
    found_first_channel = False

    # 1. Phân tách phần Header và các block Kênh
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

    # 2. Lọc kênh (Chỉ giữ nhóm yêu cầu, đuôi .m3u8 & Xóa kênh VTV lỗi)
    filtered_channels = []
    
    # Khai báo các nhóm kênh muốn giữ lại
    wanted_groups = [
        'GROUP-TITLE="VTV"',
        'GROUP-TITLE="ĐỊA PHƯƠNG"',
        'GROUP-TITLE="HTV"',
        'GROUP-TITLE="VTVCAB"',
        'GROUP-TITLE="SCTV"',
        'GROUP-TITLE="QUỐC TẾ"',
        'GROUP-TITLE="IN THE BOX"'
    ]

    print("--- BẮT ĐẦU LỌC KÊNH ---")
    for block in channels:
        extinf = block[0].upper()
        
        # 2.1. Bỏ qua kênh VTV "độ trễ thấp"
        if 'GROUP-TITLE="VTV"' in extinf and 'ĐỘ TRỄ THẤP' in extinf:
            continue
            
        # 2.2. Kiểm tra xem link stream có đuôi .m3u8 không
        is_m3u8 = False
        for line in block:
            line_clean = line.strip().lower()
            # Tìm dòng chứa link (không bắt đầu bằng # và bắt đầu bằng http)
            if not line_clean.startswith('#') and line_clean.startswith('http'):
                # Bỏ qua các tham số phía sau dấu '?' (nếu có) để lấy đuôi file thực sự
                link_base = line_clean.split('?')[0]
                if link_base.endswith('.m3u8'):
                    is_m3u8 = True
                break # Đã tìm thấy link, thoát khỏi vòng lặp kiểm tra link này
                
        # Nếu kênh không có link m3u8 thì bỏ qua luôn
        if not is_m3u8:
            continue
            
        # 2.3. Kiểm tra xem kênh này có nằm trong danh sách wanted_groups không
        is_wanted = False
        for group in wanted_groups:
            if group in extinf:
                is_wanted = True
                break
                
        # Nếu kênh thuộc nhóm mong muốn và pass hết các điều kiện trên
        if is_wanted:
            filtered_channels.append(block)

    print(f"Đã giữ lại {len(filtered_channels)} kênh hợp lệ (chỉ đuôi .m3u8).")

    # 3. Đặt mức độ ưu tiên để sắp xếp thứ tự
    def get_priority(block):
        extinf = block[0].upper()
        if 'GROUP-TITLE="VTV"' in extinf:
            return 0
        elif 'GROUP-TITLE="ĐỊA PHƯƠNG"' in extinf:
            return 1
        elif 'GROUP-TITLE="HTV"' in extinf:
            return 2
        elif 'GROUP-TITLE="VTVCAB"' in extinf:
            return 3
        elif 'GROUP-TITLE="SCTV"' in extinf:
            return 4
        elif 'GROUP-TITLE="QUỐC TẾ"' in extinf:
            return 5
        elif 'GROUP-TITLE="IN THE BOX"' in extinf:
            return 6
        else:
            return 7

    # Sắp xếp lại danh sách
    filtered_channels.sort(key=get_priority)

    # 4. Ghi ra file
    with open(FILE_PATH, 'w', encoding='utf-8') as f:
        f.writelines(header_lines)
        for block in filtered_channels:
            f.writelines(block)

    print("Đã tải, lọc, sắp xếp và lưu thành công!")

if __name__ == '__main__':
    download_and_sort_playlist()
