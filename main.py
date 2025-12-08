from core.agent_coordinator import FinancialAssistantAgent
import argparse


def main():
    parser = argparse.ArgumentParser(description="Financial Assistant Agent")
    parser.add_argument("--user-id", type=str, default="default_user", help="User ID for conversation tracking")
    args = parser.parse_args()

    # 初始化Agent
    agent = FinancialAssistantAgent()

    print("欢迎使用财经知识助手Agent！输入'退出'结束对话。")

    try:
        while True:
            user_query = input("\n您的问题: ")
            if user_query.lower() in ["退出", "q", "quit"]:
                print("感谢使用，再见！")
                break

            response = agent.process_query(args.user_id, user_query)
            print(f"\n助手回答: {response}")
    finally:
        agent.close()


if __name__ == "__main__":
    main()