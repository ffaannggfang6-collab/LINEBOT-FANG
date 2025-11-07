import os
from flask import Flask, request, abort, send_file
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, TextMessage, ImageMessage, TextSendMessage, ImageSendMessage, UnsendEvent
)
from datetime import datetime
import pytz

app = Flask(__name__)

# ======= ใส่ TOKEN / SECRET ของฟ่าง =======
import os
from flask import Flask, request, abort, send_file
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, TextMessage, ImageMessage, TextSendMessage,
    ImageSendMessage, UnsendEvent
)
from datetime import datetime
import pytz
from PIL import Image

app = Flask(__name__)

# ===== LINE CONFIG =====
CHANNEL_ACCESS_TOKEN = "CHJScm6eOVvEqpKzbP7Y0fYj5tVRlaA72LjvZH5Zzye9FzDZBROUF0sBVQgj31Pu52Xw9zoXTHz9syr3D6asy8RX7g+GXeHBKUr+eAHwQKtYz9pDsewuN8x1lwxp4bZeqj6C2cQ92/CBQB5nDac2owdB04t89/1O/w1cDnyilFU="
CHANNEL_SECRET = "5b32df6428ad0f8861a721bf688522c0"
YOUR_DOMAIN = "linebot-fang.onrender.com"

line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

# ======= Memory =======
message_memory = {}    # เก็บข้อความเอาไว้ก่อนโดนยกเลิก
image_memory = {}      # เก็บภาพที่ส่งมา
chat_counter = {}      # นับข้อความ/ภาพต่อห้อง

# ======= Folder =======
IMAGE_FOLDER = "images"
os.makedirs(IMAGE_FOLDER, exist_ok=True)

# ====== Serve Images ======
@app.route('/images/<path:filename>')
def serve_image(filename):
    full = os.path.join(IMAGE_FOLDER, filename)
    if os.path.exists(full):
        return send_file(full, mimetype='image/jpeg')
    return "File not found", 404

# ====== Root ======
@app.route("/")
def home():
    return "LINE Bot ทำงานปกติ 🎉"

# ====== Webhook ======
@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers.get("X-Line-Signature", "")
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    except Exception as e:
        print("Error:", e)
        abort(500)
    return "OK"


# ============= รับข้อความ =============
@handler.add(MessageEvent, message=TextMessage)
def handle_text(event):
    user_id = event.source.user_id
    group_id = getattr(event.source, "group_id", user_id)
    msg_id = event.message.id
    text = event.message.text.strip()

    # Reset counter เมื่อเจอ ###
    if text == "###":
        chat_counter[group_id] = 0
        return

    # ไม่เก็บถ้าเป็น emoji / . / @
    if text in [".", "@"] or len(text) == 1 and not text.isalnum():
        return

    # บันทึกข้อความ (กันยกเลิก)
    message_memory[msg_id] = {
        "user_id": user_id,
        "text": text
    }

    # เริ่มนับเฉพาะข้อความจริง
    chat_counter[group_id] = chat_counter.get(group_id, 0) + 1


# ============= รับรูปภาพ =============
@handler.add(MessageEvent, message=ImageMessage)
def handle_image(event):
    user_id = event.source.user_id
    group_id = getattr(event.source, "group_id", user_id)
    msg_id = event.message.id

    # ดาวน์โหลดไฟล์ภาพ
    content = line_bot_api.get_message_content(msg_id)
    file_path = os.path.join(IMAGE_FOLDER, f"{msg_id}.jpg")

    with open(file_path, "wb") as f:
        for chunk in content.iter_content():
            f.write(chunk)

    image_memory[msg_id] = {
        "user_id": user_id,
        "path": file_path
    }

    # นับภาพเป็น 1 บิน
    chat_counter[group_id] = chat_counter.get(group_id, 0) + 1


# ==
line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

# ======= ตัวเก็บข้อความและบิล =======
message_memory = {}
chat_counter = {}
bill_number = {}

# =================== Serve ภาพ ===================
@app.route('/images/<filename>')
def serve_image(filename):
    if os.path.exists(filename):
        return send_file(filename, mimetype='image/jpeg')
    return "File not found", 404

# =================== Webhook ===================
@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers.get("X-Line-Signature", "")
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        print("Invalid Signature Error")
        abort(400)
    except Exception as e:
        print("Error in /callback:", e)
        abort(500)
    return "OK"

# =================== รับข้อความ ===================
@handler.add(MessageEvent, message=TextMessage)
def handle_text(event):
    try:
        user_id = event.source.user_id
        group_id = getattr(event.source, 'group_id', user_id)
        text = event.message.text
        message_id = event.message.id

        if text.strip() == "เพิ่มประกาศ":
            bill_number[group_id] = bill_number.get(group_id, 0) + 1
            chat_counter[group_id] = {"text": 0, "image": 0}
            message_memory.clear()
            try:
                line_bot_api.push_message(group_id, TextSendMessage(
                    text=f"เริ่มนับจากประกาศนี้เป็นบิลที่ {bill_number[group_id]} 🧾"
                ))
            except Exception as e:
                print("Push message failed (เพิ่มประกาศ):", e)
            return

        if text.strip() == "###":
            counts = chat_counter.get(group_id, {"text":0,"image":0})
            total = counts["text"] + counts["image"]
            bill_no = bill_number.get(group_id, 1)
            summary = (
                f"✨สรุปบิลที่ {bill_no}✨\n"
                f"• ข้อความ: {counts['text']}\n"
                f"• ภาพ: {counts['image']}\n"
                f"🌷รวมทั้งหมด: {total} 📬"
            )
            try:
                line_bot_api.push_message(group_id, TextSendMessage(text=summary))
            except Exception as e:
                print("Push message failed (สรุปบิล):", e)
            return

        if text.strip() != ".":
            chat_counter.setdefault(group_id, {"text":0,"image":0})
            chat_counter[group_id]["text"] += 1

        message_memory[message_id] = {
            "type":"text",
            "user_id":user_id,
            "text":text,
            "timestamp":datetime.now(pytz.timezone("Asia/Bangkok")),
            "group_id":group_id
        }

    except Exception as e:
        print("Error in handle_text:", e)

# =================== รับภาพ ===================
@handler.add(MessageEvent, message=ImageMessage)
def handle_image(event):
    try:
        user_id = event.source.user_id
        group_id = getattr(event.source,'group_id',user_id)
        message_id = event.message.id

        chat_counter.setdefault(group_id, {"text":0,"image":0})
        chat_counter[group_id]["image"] += 1

        image_content = line_bot_api.get_message_content(message_id)
        image_path = f"temp_{message_id}.jpg"
        with open(image_path,"wb") as f:
            for chunk in image_content.iter_content():
                f.write(chunk)

        message_memory[message_id] = {
            "type":"image",
            "user_id":user_id,
            "image_path":image_path,
            "timestamp":datetime.now(pytz.timezone("Asia/Bangkok")),
            "group_id":group_id
        }

    except Exception as e:
        print("Error in handle_image:", e)

# =================== จับยกเลิกข้อความ/ภาพ ===================
@handler.add(UnsendEvent)
def handle_unsend(event):
    try:
        message_id = event.unsend.message_id
        if message_id not in message_memory:
            return
        data = message_memory[message_id]
        group_id = data["group_id"]
        user_id = data["user_id"]

        try:
            # ตรวจว่าอยู่ในกลุ่มหรือไม่
            if hasattr(event.source, "group_id"):
                profile = line_bot_api.get_group_member_profile(event.source.group_id, user_id)
            elif hasattr(event.source, "room_id"):
                profile = line_bot_api.get_room_member_profile(event.source.room_id, user_id)
            else:
                profile = line_bot_api.get_profile(user_id)
            display_name = profile.display_name
        except Exception as e:
            print("ไม่สามารถดึงชื่อผู้ใช้ได้:", e)
            display_name = "ไม่ทราบชื่อ"

        timestamp = data["timestamp"].strftime("%d/%m/%Y %H:%M:%S")

        if data["type"]=="text":
            text = data["text"]
            reply = (
                f"[  ข้อความที่ถูกยกเลิก  ]\n"
                f"• ผู้ส่ง: {display_name}\n"
                f"• เวลา: {timestamp}\n"
                f"• ข้อความ : {text}"
            )
            try:
                line_bot_api.push_message(group_id, TextSendMessage(text=reply))
            except Exception as e:
                print("Push message failed (ข้อความยกเลิก):", e)

        elif data["type"]=="image":
            image_path = data["image_path"]
            reply_text = (
                f"[  ข้อความที่ถูกยกเลิก  ]\n"
                f"• ผู้ส่ง: {display_name}\n"
                f"• เวลา: {timestamp}\n"
                f"• ข้อความ : ภาพถูกยกเลิก"
            )
            try:
                line_bot_api.push_message(group_id, [
                    TextSendMessage(text=reply_text),
                    ImageSendMessage(
                        original_content_url=f"https://{YOUR_DOMAIN}/images/{os.path.basename(image_path)}",
                        preview_image_url=f"https://{YOUR_DOMAIN}/images/{os.path.basename(image_path)}"
                    )
                ])
            except Exception as e:
                print("Push message failed (ภาพยกเลิก):", e)

        if group_id in chat_counter:
            chat_counter[group_id][data["type"]] = max(0, chat_counter[group_id][data["type"]]-1)

        del message_memory[message_id]

    except Exception as e:
        print("Error in handle_unsend:", e)

# =================== รัน Flask ===================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
