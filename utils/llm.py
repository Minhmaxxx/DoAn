"""
utils/llm.py — LLM Integration for Nutrition Advice
Supports Google Gemini and OpenAI GPT with graceful fallback.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Generator, Optional

ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))
import config


# ─── Prompt Template ─────────────────────────────────────────────────────────

SYSTEM_PROMPT = """Bạn là NutriBot — một chuyên gia dinh dưỡng lâm sàng người Việt Nam có 15 năm kinh nghiệm. 
Nhiệm vụ của bạn là phân tích chế độ ăn uống của người dùng và đưa ra lời khuyên THỰC TẾ, KHOA HỌC và DỄ THỰC HIỆN.

Nguyên tắc tư vấn:
- Luôn dùng tiếng Việt, thân thiện và dễ hiểu
- Đưa ra con số cụ thể (gram, kcal, %)
- Đề xuất thực phẩm Việt Nam phù hợp, dễ tìm mua
- KHÔNG đưa ra lời khuyên y tế thay thế bác sĩ
- Khuyến khích và tạo động lực cho người dùng

Định dạng phản hồi bằng Markdown với các phần:
1. **Phân tích bữa ăn hiện tại**
2. **Điểm tốt** (nếu có)
3. **Cần cải thiện** (nếu có)
4. **Đề xuất bữa tiếp theo**
5. **Mẹo dinh dưỡng**
"""


def build_nutrition_prompt(
    biometrics: dict,
    meal_data: dict,
    goal_data: dict,
) -> str:
    """
    Build a structured prompt for LLM nutritional analysis.

    Parameters
    ----------
    biometrics : dict
        User biometrics: age, gender, weight_kg, height_cm, activity_level,
        bmi, bmr, tdee.
    meal_data : dict
        Current meal: foods (list), total_calories, carbohydrate_g,
        protein_g, fat_g, fiber_g.
    goal_data : dict
        Goal info: goal_name, target_calories, macro_targets.

    Returns
    -------
    str
        Formatted prompt string to send to the LLM.
    """
    foods_str = "\n".join([
        f"  - {item['emoji']} {item['display_name']}: "
        f"{item['calories']} kcal "
        f"(khẩu phần: {item['portion_multiplier']}x chuẩn = {item['portion_g']}g)"
        for item in meal_data.get("foods", [])
    ])

    prompt = f"""
## Thông tin người dùng
- **Tuổi:** {biometrics.get('age', '?')} tuổi | **Giới tính:** {biometrics.get('gender', '?')}
- **Chiều cao:** {biometrics.get('height_cm', '?')} cm | **Cân nặng:** {biometrics.get('weight_kg', '?')} kg
- **BMI:** {biometrics.get('bmi', '?')} ({biometrics.get('bmi_category', '?')})
- **Mức độ vận động:** {biometrics.get('activity_level', '?')}
- **TDEE:** {biometrics.get('tdee', '?')} kcal/ngày
- **Mục tiêu sức khỏe:** {goal_data.get('goal_name', '?')}
- **Mục tiêu calo/ngày:** {goal_data.get('target_calories', '?')} kcal

## Bữa ăn vừa phân tích (HITL-adjusted)
{foods_str}

**Tổng kết bữa ăn:**
- Calo: **{meal_data.get('total_calories', 0)} kcal**
  (= {round(meal_data.get('total_calories', 0) / goal_data.get('target_calories', 2000) * 100, 1)}% mục tiêu ngày)
- Carb: {meal_data.get('carbohydrate_g', 0)}g
- Protein: {meal_data.get('protein_g', 0)}g
- Fat: {meal_data.get('fat_g', 0)}g
- Chất xơ: {meal_data.get('fiber_g', 0)}g

**Mục tiêu macro/ngày:**
- Carb: {goal_data.get('macro_targets', {}).get('carbohydrate_g', '?')}g
- Protein: {goal_data.get('macro_targets', {}).get('protein_g', '?')}g
- Fat: {goal_data.get('macro_targets', {}).get('fat_g', '?')}g

Hãy phân tích bữa ăn này và đưa ra lời khuyên cá nhân hóa dựa trên thông tin trên.
"""
    return prompt.strip()


# ─── LLM Client ──────────────────────────────────────────────────────────────

class NutriLLM:
    """
    Unified LLM interface supporting Gemini and OpenAI.

    Usage
    -----
    >>> llm = NutriLLM()
    >>> for chunk in llm.stream_advice(biometrics, meal_data, goal_data):
    ...     print(chunk, end="")
    """

    def __init__(self):
        self.provider = config.LLM_PROVIDER
        self._gemini_model = None
        self._openai_client = None

    def is_configured(self) -> bool:
        """Check if an API key is available."""
        if self.provider == "gemini":
            return bool(config.GEMINI_API_KEY)
        return bool(config.OPENAI_API_KEY)

    def _get_gemini(self):
        """Lazy-init Gemini client."""
        if self._gemini_model is None:
            import google.generativeai as genai
            genai.configure(api_key=config.GEMINI_API_KEY)
            self._gemini_model = genai.GenerativeModel(
                model_name=config.GEMINI_MODEL,
                system_instruction=SYSTEM_PROMPT,
                generation_config={
                    "max_output_tokens": config.LLM_MAX_TOKENS,
                    "temperature": config.LLM_TEMPERATURE,
                },
            )
        return self._gemini_model

    def _get_openai(self):
        """Lazy-init OpenAI client."""
        if self._openai_client is None:
            from openai import OpenAI
            self._openai_client = OpenAI(api_key=config.OPENAI_API_KEY)
        return self._openai_client

    def generate_advice(
        self,
        biometrics: dict,
        meal_data: dict,
        goal_data: dict,
    ) -> str:
        """
        Generate nutrition advice (non-streaming).

        Returns
        -------
        str
            Full advice text in Markdown.
        """
        prompt = build_nutrition_prompt(biometrics, meal_data, goal_data)

        if not self.is_configured():
            return self._demo_advice(meal_data, goal_data)

        try:
            if self.provider == "gemini":
                model = self._get_gemini()
                response = model.generate_content(prompt)
                return response.text

            else:  # openai
                client = self._get_openai()
                response = client.chat.completions.create(
                    model=config.OPENAI_MODEL,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                    max_tokens=config.LLM_MAX_TOKENS,
                    temperature=config.LLM_TEMPERATURE,
                )
                return response.choices[0].message.content

        except Exception as e:
            return (
                f" **Lỗi kết nối AI:** {e}\n\n"
                "Vui lòng kiểm tra API key trong file `.env` và thử lại."
            )

    def stream_advice(
        self,
        biometrics: dict,
        meal_data: dict,
        goal_data: dict,
    ) -> Generator[str, None, None]:
        """
        Stream nutrition advice token by token for real-time display.

        Yields
        ------
        str
            Text chunks as they arrive from the LLM.
        """
        prompt = build_nutrition_prompt(biometrics, meal_data, goal_data)

        if not self.is_configured():
            yield self._demo_advice(meal_data, goal_data)
            return

        try:
            if self.provider == "gemini":
                model = self._get_gemini()
                stream = model.generate_content(prompt, stream=True)
                for chunk in stream:
                    if chunk.text:
                        yield chunk.text

            else:  # openai
                client = self._get_openai()
                stream = client.chat.completions.create(
                    model=config.OPENAI_MODEL,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                    max_tokens=config.LLM_MAX_TOKENS,
                    temperature=config.LLM_TEMPERATURE,
                    stream=True,
                )
                for chunk in stream:
                    delta = chunk.choices[0].delta.content
                    if delta:
                        yield delta

        except Exception as e:
            yield f"\n\n **Lỗi kết nối AI:** {e}\n\nVui lòng kiểm tra API key."

    def _demo_advice(self, meal_data: dict, goal_data: dict) -> str:
        """Return demo advice when no API key is configured."""
        total_cal = meal_data.get("total_calories", 0)
        target_cal = goal_data.get("target_calories", 2000)
        remaining = target_cal - total_cal

        return f"""
## Phân tích bữa ăn hiện tại

>  *Đây là phân tích mẫu. Để nhận tư vấn cá nhân hóa từ AI, hãy thêm API key vào file `.env`.*

Bữa ăn của bạn cung cấp **{total_cal} kcal**, chiếm 
**{round(total_cal/target_cal*100, 1)}%** mục tiêu calo ngày ({target_cal} kcal).

## Điểm tốt
- Bạn đã theo dõi lượng calo — đây là bước đầu tiên và quan trọng nhất!
- Các món ăn Việt Nam truyền thống thường giàu chất xơ và protein.

## Cần cải thiện
- Hãy đảm bảo uống đủ **2-2.5 lít nước** mỗi ngày.
- Bổ sung thêm rau xanh và trái cây để tăng vitamin.

## Đề xuất bữa tiếp theo
Bạn còn khoảng **{max(0, remaining):.0f} kcal** cho phần còn lại của ngày. Gợi ý:
- Bữa nhẹ: Gỏi cuốn tươi (~180 kcal) + trái cây tươi
- Bữa tối: Cháo lòng (~380 kcal) với nhiều rau

## Mẹo dinh dưỡng hôm nay
Ăn chậm, nhai kỹ — não cần 20 phút để nhận tín hiệu no từ dạ dày. 
Điều này giúp bạn ăn ít hơn 10-20% mà vẫn cảm thấy đủ no!
""".strip()
