import json
import os

# 输入文件名
input_file = "./mcp_server/local_sai_search/src/database_json/result.jsonl"
# 输出文件名 (对应你 rag_service.py 里调用的名字)
output_file = "./mcp_server/local_sai_search/src/database_json/fix_json.json"

def clean_and_convert():
    # 确保输出目录存在
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    cleaned_data = []
    success_count = 0
    
    print(f"🔄 正在读取 {input_file}...")
    
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f):
                line = line.strip()
                if not line: continue
                
                try:
                    # 1. 解析每一行原始数据
                    raw_item = json.loads(line)
                    
                    # 2. 提取核心字段 (从 extracted 里面拿)
                    # 注意：根据你上传的文件，有效数据都在 'extracted' 字段里
                    if 'extracted' in raw_item:
                        extracted = raw_item['extracted']
                        
                        # 3. 构建新的精简对象
                        new_item = {
                            "summary": extracted.get("summary", ""),
                            "content": extracted.get("content", ""),
                            "source_url": raw_item.get("input", {}).get("meta_info", {}).get("url", "") #以此保留URL作为元数据
                        }
                        
                        # 只有当 summary 不为空时才添加
                        if new_item["summary"]:
                            cleaned_data.append(new_item)
                            success_count += 1
                            
                except json.JSONDecodeError:
                    print(f"⚠️ 第 {line_num+1} 行格式错误，已跳过")
                    
        # 4. 写入标准 JSON 列表格式
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(cleaned_data, f, ensure_ascii=False, indent=4)
            
        print(f"\n✅ 转换成功！")
        print(f"📄 共处理有效数据: {success_count} 条")
        print(f"💾 已保存至: {output_file}")
        print(f"👀 数据预览 (第一条):")
        if cleaned_data:
            print(json.dumps(cleaned_data[0], ensure_ascii=False, indent=2))

    except FileNotFoundError:
        print(f"❌ 错误: 找不到输入文件 {input_file}")

if __name__ == "__main__":
    clean_and_convert()