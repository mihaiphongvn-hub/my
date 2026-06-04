import urllib.request
import os

# Link chứa file M3U gốc của bạn
URL = 'https://vpsttt.vietanhtv.top/tv/' 
# Tên file bạn muốn lưu trên GitHub
FILE_PATH = 'playlist.m3u'

def download_and_sort_playlist():
    print(f"Đang tải dữ liệu từ {URL}...")
    try:
        # Thêm Header User-Agent để tránh bị máy chủ chặn (lỗi 403)
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

    # Đặt mức độ ưu tiên
    def get_priority(block):
        extinf = block[0].upper()
        if 'GROUP-TITLE="VTV"' in extinf:
            return 0 # Ưu tiên cao nhất
        elif 'GROUP-TITLE="ĐỊA PHƯƠNG"' in extinf:
            return 1 # Ưu tiên thứ 2
        else:
            return 2 # Các kênh còn lại

    # Sắp xếp
    channels.sort(key=get_priority)

    # Ghi ra file
    with open(FILE_PATH, 'w', encoding='utf-8') as f:
        f.writelines(header_lines)
        for block in channels:
            f.writelines(block)

    print("Đã tải, sắp xếp (VTV & Địa Phương lên đầu) và lưu thành công!")

if __name__ == '__main__':
    download_and_sort_playlist()
