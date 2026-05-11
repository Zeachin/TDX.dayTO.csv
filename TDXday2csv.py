import os
import struct
import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed  # 直接从futures导入as_completed

def collect_all_stock_codes(src_dirs):
    """收集所有股票代码，检测冲突"""
    code_count = {}
    all_files = []
    
    for market, src_dir in src_dirs.items():
        if os.path.exists(src_dir):
            for filename in os.listdir(src_dir):
                if filename.endswith('.day'):
                    code = filename[:-4][2:]  # 去掉前缀后的数字代码
                    prefix = filename[:-4][:2]  # 市场前缀
                    # 筛选股票代码前两位为00或60的文件
                    if code[:2] in ('00', '60'):
                        all_files.append((market, src_dir, filename, code, prefix))
                        code_count[code] = code_count.get(code, 0) + 1
    
    # 返回重复的代码列表
    duplicate_codes = {code for code, count in code_count.items() if count > 1}
    return all_files, duplicate_codes


def process_file(src_path, dst_path, market):
    """单个文件处理函数，用于多线程"""
    try:
        stock_csv(src_path, os.path.basename(src_path)[:-4][2:], dst_path)
        print(f"完成处理: {src_path} -> {dst_path}")
    except Exception as e:
        print(f"处理失败: {src_path} -> {dst_path}, 错误: {e}")


def process_all_files(all_files, duplicate_codes, dst_dir, max_workers=5):
    """处理所有文件，智能命名：无冲突用数字代码，有冲突保留前缀"""
    if not os.path.exists(dst_dir):
        os.makedirs(dst_dir)
        
    tasks = []
    file_count = 0
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for market, src_dir, filename, code, prefix in all_files:
            src_path = os.path.join(src_dir, filename)
            # 如果代码重复，保留前缀；否则只使用数字代码
            if code in duplicate_codes:
                dst_file_name = f"{prefix}{code}.csv"
            else:
                dst_file_name = f"{code}.csv"
            dst_path = os.path.join(dst_dir, dst_file_name)
            tasks.append(executor.submit(process_file, src_path, dst_path, market))
            file_count += 1
        
        # 等待所有任务完成
        for future in as_completed(tasks): 
            try:
                future.result()
            except Exception as exc:
                print(f"生成文件时发生了错误: {exc}")
    
    return file_count, len(duplicate_codes)


def stock_csv(filepath, name, output_path):
    """解析单个.day文件并输出为CSV，包含列标题，数值保留两位小数"""
    with open(filepath, 'rb') as f:
        with open(output_path, 'w+', encoding='utf-8') as file_object:
            # 写入列标题
            file_object.write("date,open,high,low,close,volume\n")
            
            while True:
                stock_date = f.read(4)
                if not stock_date:
                    break
                stock_open = f.read(4)
                stock_high = f.read(4)
                stock_low = f.read(4)
                stock_close = f.read(4)
                stock_amount = f.read(4)
                stock_vol = f.read(4)
                stock_reservation = f.read(4)
                
                stock_date = struct.unpack("l", stock_date)[0]
                stock_open = round(struct.unpack("l", stock_open)[0] / 100, 2)  # 保留两位小数
                stock_high = round(struct.unpack("l", stock_high)[0] / 100, 2)
                stock_low = round(struct.unpack("l", stock_low)[0] / 100, 2)
                stock_close = round(struct.unpack("l", stock_close)[0] / 100, 2)
                stock_amount = struct.unpack("f", stock_amount)[0]  # 成交额，保持浮点数
                stock_vol = struct.unpack("l", stock_vol)[0]  # 成交量，通常为整数，不需要格式化为两位小数
                
                date_format = datetime.datetime.strptime(str(stock_date), '%Y%m%d')
                line = f"{date_format.strftime('%Y-%m-%d')},{stock_open:.2f},{stock_high:.2f},{stock_low:.2f},{stock_close:.2f},{stock_vol}\n"
                
                file_object.write(line)


# 主处理流程
src_dirs = {
    'sh': 'D:/海王星金融终端-中国银河证券/vipdoc/sh/lday',# 此处需要更改为通达信上海日线数据存储的实际目录
    'sz': 'D:/海王星金融终端-中国银河证券/vipdoc/sz/lday',# 此处需要更改为通达信深圳日线数据存储的实际目录
    'bj': 'D:/海王星金融终端-中国银河证券/vipdoc/bj/lday' # 此处需要更改为通达信深圳日线数据存储的实际目录
}
dst_base_dir = 'D:/lDay2csv/csv'# 此处需要更改为解析后的CSV文件的存储目录

# 生成今日日期文件夹名，格式为 csv260101（年份后两位+月份+日期）
today = datetime.datetime.now()
date_folder_name = f"csv{today.strftime('%y%m%d')}"
dst_dir = os.path.join(dst_base_dir, date_folder_name)

# 收集所有文件并检测冲突
print("正在扫描所有源文件...")
all_files, duplicate_codes = collect_all_stock_codes(src_dirs)

if duplicate_codes:
    print(f"检测到 {len(duplicate_codes)} 个重复代码，将为这些文件保留市场前缀")
    print(f"重复代码示例: {list(duplicate_codes)[:5]}...")
else:
    print("未检测到重复代码")

# 处理所有文件
print("开始处理所有市场数据...")
total_files, duplicate_count = process_all_files(all_files, duplicate_codes, dst_dir)

print(f"共计导出csv文件{total_files}个")
print(f"其中 {duplicate_count} 个代码存在冲突，已保留市场前缀")
print(f"全部搞定，输出文件已保存到: {dst_dir}")