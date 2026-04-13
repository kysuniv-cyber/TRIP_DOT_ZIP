# constants.py
# 시스템 프롬프트, 설정값 등 변하지 않는 값들 여기서 관리
OPENAI_MODEL    = "gpt-4o-mini"
CSS_FILE_PATH   = "\assets\styles.css"

# ============================
# MAP 사용 template
# ============================
# tool tip template
TOOLTIP_TEMPLATE = "{order}. {name}"

# popup template
POPUP_TEMPLATE = """
<div style='font-family: sans-serif;'>
    <b style='font-size: 14px;'>{order}.{name}</b><br>
    <hr style='margin: 5px 0;'>
</div>
"""

# icon template
MARKER_ICON_TEMPLATE = """
<div style="background:#4A90E2;color:white;border-radius:50%;width:28px;height:28px;line-height:28px;text-align:center;font-weight:bold">
    {order}
</div>
"""
