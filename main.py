from llm.qwen_vl import analyze_snowboard_image
from pricing.pricing_engine import estimate_secondhand_price


def main():
    image_path = r"C:\DownLoads\snowboard\1.jpg"

    # 1. 图像分析（模型）
    analysis_result = analyze_snowboard_image(image_path)

    # # 2. 定价分析（规则）
    price_result = estimate_secondhand_price(analysis_result)

    # 3. 输出
    print("\n===== 雪板分析结果 =====")
    for k, v in analysis_result.items():
        print(f"{k}: {v}")

    #
    print("\n===== 定价与购买建议 =====")
    for k, v in price_result.items():
        print(f"{k}: {v}")


if __name__ == "__main__":
    main()
