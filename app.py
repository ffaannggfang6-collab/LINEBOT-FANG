import os
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, ImageMessage, TextSendMessage, UnsendEvent
from datetime import datetime
import pytz

app = Flask(__name__)

# ======= TOKEN / SECRET / DOMAIN =======
CHANNEL_ACCESS_TOKEN = "CHJScm6eOVvEqpKzbP7Y0fYj5tVRlaA72LjvZH5Zzye9FzDZBROUF0sBVQgj31Pu52Xw9zoXTHz9syr3D6asy8RX7g+GXeHBKUr+eAHwQKtYz9pDsewuN8x1lwxp4bZeqj6C2cQ92/CBQB5nDac2owdB04t89/1O/w1cDnyilFU="
CHANNEL_SECRET = "5b32df6428ad0f8861a721bf688522c0"
YOUR_DOMAIN = "https://linebot-fang.onrender.com"

line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

# ======= ตัวเก็บข้อความ =======
message_memory = {}
message_log = {}
counter = {}

# ======= Root =======
@app.route("/")
def home():
    return "LINE Bot Running ✅"

# ======= Webhook =======
@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers.get("X-Line-Signature", "")
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return "OK"

# ======= รับข้อความ (เก็บ log + นับข้อความ) =======
@handler.add(MessageEvent, message=TextMessage)
def handle_text(event):
    user_id = event.source.user_id
    group_id = getattr(event.source, "group_id", user_id)

    # นับข้อความ
    counter[group_id] = counter.get(group_id, 0) + 1

    # เก็บข้อความสำหรับ unsend
    message_log[event.message.id] = event.message.text

    # AUTO Reply (ทดสอบ)
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=f"ข้อความที่ {counter[group_id]} ✅")
    )

# ======= รับภาพ (บันทึก message id เฉย ๆ ตอนนี้) =======
@handler.add(MessageEvent, message=ImageMessage)
def handle_image(event):
    message_log[event.message.id] = "<image>"
    # ไม่ต้องตอบก็ได้เพื่อความเงียบ
    pass

# ======= เมื่อมีการ unsend =======
@handler.add(UnsendEvent)
def handle_unsend(event):
    msg_id = event.unsend.message_id
    text = message_log.get(msg_id, "ไม่พบข้อมูลข้อความ")

    reply = f"มีการยกเลิกข้อความ ❗\n\nเนื้อหา:\n{text}"

    line_bot_api.push_message(
        event.source.user_id,
        TextSendMessage(text=reply)
    )
