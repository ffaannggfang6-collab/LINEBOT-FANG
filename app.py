import os
from flask import Flask, request, abort, send_file
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import *
from datetime import datetime
import pytz

app = Flask(__name__)

# ===== LINE CONFIG =====
CHANNEL_ACCESS_TOKEN = "CHJScm6eOVvEqpKzbP7Y0fYj5tVRlaA72LjvZH5Zzye9FzDZBROUF0sBVQgj31Pu52Xw9zoXTHz9syr3D6asy8RX7g+GXeHBKUr+eAHwQKtYz9pDsewuN8x1lwxp4bZeqj6C2cQ92/CBQB5nDac2owdB04t89/1O/w1cDnyilFU="
CHANNEL_SECRET = "5b32df6428ad0f8861a721bf688522c0"
YOUR_DOMAIN = "https://linebot-fang.onrender.com"
line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

# ===== MEMORY =====
message_memory = {}  # เก็บข้อความที่ส่งเข้ามา
image_memory = {}    # เก็บภาพ
count_text = 0
count_image = 0
counting = False

# ======= Folder =======
IMAGE_FOLDER = "images"
os.makedirs(IMAGE_FOLDER, exist_ok=True)

@app.route("/")
def home():
    return "Bot Running ✅"

@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers.get("X-Line-Signature", "")
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return "OK"

def is_valid_message(text):
    if not text:
        return False
    if text in [".", "@"]:
        return False
    if any(ch in text for ch in "😀😁😂🤣😅😆😉😊😋😎😍😘😗😙😚🙂🤗🤔😐😑😶🙄😏😣😥😮🤐😯😪😫😴😌😛😜😝🤤😒😓😔😕🙃🤑😲☹🙁😖😞😟"):
        return False
    return text.replace(" ", "").isdigit()

# ===== รับข้อความ =====
@handler.add(MessageEvent, message=TextMessage)
def handle_text(event):
    global count_text, count_image, counting

    user_id = event.source.user_id
    group_id = getattr(event.source, "group_id", user_id)
    text = event.message.text.strip()

    # เริ่มนับเมื่อมีคำว่า "เพิ่มประกาศ"
    if text == "เพิ่มประกาศ":
        counting = True
        count_text = 0
        count_image = 0
        line_bot_api.reply_message(event.reply_token, TextMessage(text="เริ่มนับบิลแล้วค่ะ ✅"))
        return

    # คำสั่งสรุปบิล ###
    if text == "###":
        total = count_text + count_image
        summary = (
            "✨สรุปบิล✨\n"
            f"• ข้อความ: {count_text}\n"
            f"• ภาพ: {count_image}\n"
            f"🌷รวมทั้งหมด: {total} 📬"
        )
        line_bot_api.reply_message(event.reply_token, TextMessage(text=summary))
        return

    # เก็บข้อความเพื่อตรวจจับ unsend
    message_memory[event.message.id] = {"text": text, "user_id": user_id, "group_id": group_id}

    # ถ้านับอยู่ และเป็นข้อความบิน → เพิ่ม 1
    if counting and is_valid_message(text):
        count_text += 1

# ===== รับภาพ =====
@handler.add(MessageEvent, message=ImageMessage)
def handle_image(event):
    global count_image, counting

    user_id = event.source.user_id
    group_id = getattr(event.source, "group_id", user_id)

    # ดาวน์โหลดภาพเก็บไว้
    image_content = line_bot_api.get_message_content(event.message.id)
    filename = f"{event.message.id}.jpg"
    filepath = os.path.join(IMAGE_FOLDER, filename)

    with open(filepath, 'wb') as f:
        for chunk in image_content.iter_content():
            f.write(chunk)

    image_memory[event.message.id] = {"path": filepath, "user_id": user_id, "group_id": group_id}

    if counting:
        count_image += 1

# ===== จับยกเลิกข้อความ/ภาพ =====
@handler.add(UnsendEvent)
def handle_unsend(event):
    msg_id = event.unsend.message_id

    # ===== ลบข้อความ =====
    if msg_id in message_memory:
        data = message_memory.pop(msg_id)
        user_name = line_bot_api.get_profile(data["user_id"]).display_name
        now = datetime.now(pytz.timezone("Asia/Bangkok")).strftime("%d/%m/%Y %H:%M:%S")
        reply = (
            "[ ข้อความที่ถูกยกเลิก ]\n"
            f"• ผู้ส่ง: {user_name}\n"
            f"• เวลา: {now}\n"
            f"• ข้อความ: {data['text']}"
        )
        line_bot_api.push_message(data["group_id"], TextMessage(text=reply))
        return

    # ===== ลบภาพ =====
    if msg_id in image_memory:
        data = image_memory.pop(msg_id)
        user_name = line_bot_api.get_profile(data["user_id"]).display_name
        now = datetime.now(pytz.timezone("Asia/Bangkok")).strftime("%d/%m/%Y %H:%M:%S")

        reply = (
            "[ ภาพที่ถูกยกเลิก ]\n"
            f"• ผู้ส่ง: {user_name}\n"
            f"• เวลา: {now}\n"
            f"• ภาพ: (ส่งด้านล่าง)"
        )

        line_bot_api.push_message(data["group_id"], TextMessage(text=reply))
        line_bot_api.push_message(data["group_id"], ImageSendMessage(
            original_content_url=f"https://{YOUR_DOMAIN}/images/{os.path.basename(data['path'])}",
            preview_image_url=f"https://{YOUR_DOMAIN}/images/{os.path.basename(data['path'])}"
        ))
