#!/usr/bin/env python3
"""
AI 资讯发送到飞书脚本 (V4)
使用优化版 fetch_ai_news_v4，改进分类逻辑
"""
import subprocess
import sys
import os

# 获取脚本所在目录
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# 飞书目标用户
FEISHU_USER_ID = "ou_5b479a8489e8ebf34df50794d2a2cb0d"


def get_news_content():
    """获取 AI 资讯内容"""
    sys.path.insert(0, SCRIPT_DIR)
    import fetch_ai_news_v4
    
    content = fetch_ai_news_v4.get_news_summary(days=1)
    return content


def send_to_feishu(content):
    """发送消息到飞书"""
    cmd = [
        "openclaw", "message", "send",
        "--channel", "feishu",
        "--account", "fs_news_claw",
        "--target", f"user:{FEISHU_USER_ID}",
        "--message", content
    ]

    try:
        print(f"执行命令: {' '.join(cmd[:6])}...")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

        print(f"返回码: {result.returncode}")
        if result.stdout:
            print(f"标准输出:\n{result.stdout}")
        if result.stderr:
            print(f"错误输出:\n{result.stderr}")

        if result.returncode == 0:
            print(f"✅ 消息发送成功")
            return True
        else:
            print(f"❌ 消息发送失败 (返回码: {result.returncode})")
            return False
    except subprocess.TimeoutExpired:
        print(f"❌ 发送超时 (超过120秒)")
        return False
    except Exception as e:
        print(f"❌ 发送错误: {str(e)}")
        return False


def main():
    """主函数"""
    print("=" * 50)
    print("📰 AI 资讯发送任务 (V4 - 优化分类)")
    print("=" * 50)
    print("\n1️⃣ 获取 AI 资讯...")
    
    content = get_news_content()
    
    if not content:
        print("❌ 获取资讯失败")
        return 1
    
    content_length = len(content)
    print(f"✅ 获取到 {content_length} 字节的资讯内容")
    
    print(f"\n2️⃣ 发送消息到飞书...")
    print(f"   目标用户: {FEISHU_USER_ID}")
    
    success = send_to_feishu(content)
    
    print("\n" + "=" * 50)
    if success:
        print("✅ AI 资讯发送完成")
        return 0
    else:
        print("❌ AI 资讯发送失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())
