# -*- coding: utf-8 -*-
"""文件解析器测试"""
import sys, os, json, csv, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from crawlers.utils.file_parser import FileParser

def main():
    parser = FileParser()
    
    # Test 1: CSV
    print("=" * 40)
    print("Test 1: CSV 解析")
    csv_path = os.path.join(tempfile.gettempdir(), "test_data.csv")
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["name", "age", "score"])
        writer.writerow(["Alice", "25", "95.5"])
        writer.writerow(["Bob", "30", "87.3"])
        writer.writerow(["Charlie", "28", "92.1"])
    
    result = parser.parse_file(csv_path)
    print(f"  Type: {result['file_type']}")
    print(f"  Rows: {result['row_count']}")
    print(f"  Columns: {result['columns']}")
    print(f"  Dtypes: {result['dtypes']}")
    print(f"  Preview: {result['preview']}")
    assert result["row_count"] == 3
    print("  PASS")
    
    # Test 2: JSON
    print("\n" + "=" * 40)
    print("Test 2: JSON 解析")
    json_path = os.path.join(tempfile.gettempdir(), "test_data.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump([
            {"city": "Beijing", "temp": 22.5},
            {"city": "Shanghai", "temp": 25.0},
            {"city": "Guangzhou", "temp": 28.3},
        ], f, ensure_ascii=False)
    
    result = parser.parse_file(json_path)
    print(f"  Type: {result['file_type']}")
    print(f"  Rows: {result['row_count']}")
    print(f"  Dtypes: {result['dtypes']}")
    assert result["row_count"] == 3
    print("  PASS")
    
    # Test 3: 自动检测类型
    print("\n" + "=" * 40)
    print("Test 3: 自动检测")
    detected = parser._detect_file_type("data.csv")
    print(f"  .csv -> {detected}")
    assert detected == "csv"
    
    detected = parser._detect_file_type("data.json")
    print(f"  .json -> {detected}")
    assert detected == "json"
    
    detected = parser._detect_file_type("data.xlsx")
    print(f"  .xlsx -> {detected}")
    assert detected == "excel"
    print("  PASS")
    
    # Test 4: 类型推断
    print("\n" + "=" * 40)
    print("Test 4: 类型推断")
    rows = [
        {"name": "A", "age": "25", "score": "95.5"},
        {"name": "B", "age": "30", "score": "87.3"},
    ]
    dtypes = parser._infer_dtypes(rows, ["name", "age", "score"])
    print(f"  Dtypes: {dtypes}")
    assert dtypes["name"] == "string"
    assert dtypes["age"] == "integer"
    assert dtypes["score"] == "float"
    print("  PASS")
    
    print("\nAll file parser tests passed!")

if __name__ == "__main__":
    main()
