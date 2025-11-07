import os
from flask import Flask, request, abort, send_file
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, TextMessage, ImageMessage,
    TextSendMessage, ImageSendMessage, UnsendEvent
)
from datetime import datetime
import pytz

app = Flask(__name__)

# ======= TOKEN / SECRET / DOMAIN =======
CHANNEL_ACCESS_TOKEN = "CHJScm6eOVvEqpKzbP7Y0fYj5tVRlaA72LjvZH5Zzye9FzDZBROUF0sBVQgj31Pu52Xw9zoXTHz9syr3D6asy8RX7g+GXeHBKUr+eAHwQKtYz9pDsewuN8x1lwxp4bZeqj6C2cQ92/CBQB5nDac2owdB04t89/1O/w1cDnyilFU="
CHANNEL_SECRET = "5b32df6428ad0f8861a721bf688522c0"
YOUR_DOMAIN = "linebot-fang.onrender.com"

line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

# ======= Memory =======
message_memory = {}
chat_counter = {}

# ======= Folder เก็บภาพ =======
IMAGE_FOLDER = "images"
os.makedirs(IMAGE_FOLDER, exist_ok=True)

# ======= Serve images =======
@app.route('/images/<filename>')
def serve_image(filename):
    full_path = os.path.join(IMAGE_FOLDER, filename)
    if os.path.exists(full_path):
        return send_file(full_path, mimetype='image/jpeg')
    return "File not found", 404

# ======= Root =======
@app.route("/")
def home():
    return "LINE Bot ทำงานปกติ 🎉"

# ======= Webhook =======
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

# ======= รับข้อความ =======
@handler.add(MessageEvent, message=TextMessage)
def handle_text(event):
    try:
        user_id = event.source.user_id
        group_id = getattr(event.source,'group_id',user_id)
        message_id = event.message.id
        text = event.message.text.strip()

        # ---------- เริ่มนับบิลใหม่ ----------
        if text == "เพิ่มประกาศ":
            chat_counter[group_id] = {"text":0,"image":0}  # รีเซ็ต
            line_bot_api.push_message(
                group_id,
                TextSendMessage(text="📌 เพิ่มประกาศใหม่ / เริ่มนับบิลใหม่เรียบร้อยแล้ว")
            )
            return

        # ---------- สรุปยอดบิล ----------
        if text == "###":
            counter = chat_counter.get(group_id, {"text":0,"image":0})
            total = counter["text"] + counter["image"]
            reply = (
                "✨สรุปบิล✨\n"
                f"• ข้อความ: {counter['text']}\n"
                f"• ภาพ: {counter['image']}\n"
                f"🌷รวมทั้งหมด: {total}📝"
            )
            line_bot_api.push_message(group_id, TextSendMessage(text=reply))
            return

        # ---------- ไม่นับ emoji / . / @ ----------
        if text in [".","@"] or len(text)==1 and not text.isalnum():
            return

        # ---------- บันทึกข้อความ ----------
        message_memory[message_id] = {
            "type":"text",
            "user_id":user_id,
            "text":text,
            "timestamp":datetime.now(pytz.timezone("Asia/Bangkok")),
            "group_id":group_id
        }

        # ---------- นับข้อความ ----------
        chat_counter.setdefault(group_id, {"text":0,"image":0})
        chat_counter[group_id]["text"] += 1

    except Exception as e:
        print("Error in handle_text:", e)

# ======= รับภาพ =======
@handler.add(MessageEvent, message=ImageMessage)
def handle_image(event):
    try:
        user_id = event.source.user_id
        group_id = getattr(event.source,'group_id',user_id)
        message_id = event.message.id

        chat_counter.setdefault(group_id, {"text":0,"image":0})
        chat_counter[group_id]["image"] += 1

        # ดาวน์โหลดภาพ
        image_content = line_bot_api.get_message_content(message_id)
        image_path = os.path.join(IMAGE_FOLDER, f"{message_id}.jpg")
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

# ======= จับยกเลิกข้อความ/ภาพ =======
@handler.add(UnsendEvent)
def handle_unsend(event):
    try:
        message_id = event.unsend.message_id
        if message_id not in message_memory:
            return
        data = message_memory.pop(message_id)
        group_id = data["group_id"]
        user_id = data["user_id"]

        # ดึงชื่อผู้ส่ง
        try:
            if hasattr(event.source, "group_id"):
                profile = line_bot_api.get_group_member_profile(event.source.group_id, user_id)
            elif hasattr(event.source, "room_id"):
                profile = line_bot_api.get_room_member_profile(event.source.room_id, user_id)
            else:
                profile = line_bot_api.get_profile(user_id)
            display_name = profile.display_name
        except:
            display_name = "ไม่ทราบชื่อ"

        timestamp = data["timestamp"].strftime("%d/%m/%Y %H:%M:%S")

        # ====== ข้อความ ======
        if data["type"]=="text":
            text = data["text"]
            reply = (
                f"[ ข้อความที่ถูกยกเลิก ]\n"
                f"• ผู้ส่ง: {display_name}\n"
                f"• เวลา: {timestamp}\n"
                f"• ข้อความ: {text}"
            )
            line_bot_api.push_message(group_id, TextSendMessage(text=reply))

        # ====== ภาพ ======
        elif data["type"]=="image":
            image_path = data["image_path"]
            reply_text = (
                f"[ ภาพที่ถูกยกเลิก ]\n"
                f"• ผู้ส่ง: {display_name}\n"
                f"• เวลา: {timestamp}\n"
                f"• ภาพ: (ส่งภาพต้นฉบับกลับมา)"
            )
            url = f"https://{YOUR_DOMAIN}/images/{os.path.basename(image_path)}"
            line_bot_api.push_message(group_id, [
                TextSendMessage(text=reply_text),
                ImageSendMessage(
                    original_content_url=url,
                    preview_image_url=url
                )
            ])

        # ปรับ counter
        if group_id in chat_counter:
            chat_counter[group_id][data["type"]] = max(0, chat_counter[group_id][data["type"]]-1)

    except Exception as e:
        print("Error in handle_unsend:", e)

# ======= Run Flask =======
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
