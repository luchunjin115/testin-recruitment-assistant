"""数据库初始化脚本 - 建表并按需导入演示数据"""
import os
import sys

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(project_root, "backend"))
os.chdir(os.path.join(project_root, "backend"))

sys.path.insert(0, os.path.join(project_root, "scripts"))
from ensure_demo_data import ensure_demo_data

if __name__ == "__main__":
    print("正在初始化数据库...")
    generated = ensure_demo_data()
    if generated:
        print("演示数据导入完成")
    else:
        print("数据库已有候选人数据，未重复导入演示数据")
    print("数据库初始化成功！")
