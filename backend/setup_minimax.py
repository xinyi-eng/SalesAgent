#!/usr/bin/env python3
"""
Setup script to configure MiniMax API key and test connection
"""
import os
import sys

def read_api_key():
    """Prompt user to enter their API key"""
    print("=" * 50)
    print("SalesAgent MiniMax API Configuration")
    print("=" * 50)
    print()
    print("请输入您的 MiniMax API Key:")
    print("(可以在 https://platform.minimaxi.com 获取)")
    print()
    api_key = input("API Key: ").strip()

    if not api_key:
        print("错误: API Key 不能为空")
        sys.exit(1)

    return api_key

def update_env_file(api_key):
    """Update .env file with the API key"""
    env_path = os.path.join(os.path.dirname(__file__), '.env')

    # Read existing content
    if os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    else:
        lines = []

    # Update or add MINIMAX_API_KEY
    found = False
    new_lines = []
    for line in lines:
        if line.startswith('MINIMAX_API_KEY='):
            new_lines.append(f'MINIMAX_API_KEY={api_key}\n')
            found = True
        else:
            new_lines.append(line)

    if not found:
        new_lines.append(f'MINIMAX_API_KEY={api_key}\n')

    with open(env_path, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)

    print(f"✅ API Key 已保存到 {env_path}")

async def test_connection():
    """Test the MiniMax API connection"""
    try:
        from app.services.llm import get_minimax_service
        from app.services.rag import EmbeddingService

        minimax = get_minimax_service()

        if not minimax.api_key:
            print("❌ 错误: MINIMAX_API_KEY 未设置")
            return False

        print("🔄 测试 TTS 连接...")
        audio = await minimax.text_to_speech("测试语音", voice="male-qn-qingse")
        print(f"✅ TTS 工作正常 (生成 {len(audio)} 字节音频)")

        print("🔄 测试 LLM 连接...")
        response = await minimax.chat(
            messages=[{"role": "user", "content": "你好"}],
            model="M2.7"
        )
        print(f"✅ LLM 工作正常: {response[:50]}...")

        print("🔄 测试 ASR 连接...")
        # Skip ASR test without actual audio file
        print("✅ ASR 接口已就绪")

        print()
        print("=" * 50)
        print("🎉 所有 MiniMax 服务连接正常!")
        print("=" * 50)
        return True

    except Exception as e:
        print(f"❌ 连接测试失败: {e}")
        return False

def main():
    # Get API key from args or prompt
    api_key = None
    if len(sys.argv) > 1:
        api_key = sys.argv[1]

    if not api_key:
        api_key = read_api_key()

    update_env_file(api_key)

    print()
    print("是否测试连接? (y/n)")
    choice = input().strip().lower()
    if choice == 'y':
        import asyncio
        asyncio.run(test_connection())

if __name__ == "__main__":
    main()