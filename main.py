import datetime
import json
import os
import sys
import threading
import time
import urllib3
import telebot
from flask import Flask
from telebot import types

# --- AĞ VE TIMEOUT AYARLARI ---
urllib3.util.timeout.Timeout.DEFAULT_TIMEOUT = 600
telebot.apihelper.CONNECT_TIMEOUT = 600
telebot.apihelper.READ_TIMEOUT = 600

TOKEN = "8667525173:AAGyk_nkkmM9F4IcnJVQjVFu_zs5ubRnirA"

# ZORUNLU KANALLAR
ZORUNLU_KANALLAR = ["@Hurriyetxx", "@Hurriyetx"]

KURUCU = "@growxana4"
GUNLUK_LIMIT = 2
LIMIT_DOSYASI = "limitler.json"

bot = telebot.TeleBot(TOKEN)
user_data = {}

# --- RENDER UYUTMAMA SUNUCUSU (FLASK) ---
app = Flask(__name__)


@app.route("/")
def home():
  return "Bot 7/24 Aktif ve Calisiyor!"


def run_web():
  port = int(os.environ.get("PORT", 10000))
  app.run(host="0.0.0.0", port=port)


# ----------------------------------------


def limitleri_yukle():
  if os.path.exists(LIMIT_DOSYASI):
    try:
      with open(LIMIT_DOSYASI, "r", encoding="utf-8") as f:
        return json.load(f)
    except Exception:
      return {}
  return {}


def limitleri_kaydet(data):
  try:
    with open(LIMIT_DOSYASI, "w", encoding="utf-8") as f:
      json.dump(data, f, ensure_ascii=False, indent=2)
  except Exception as e:
    print(f"[HATA] Dosya yazma hatası: {e}")


kullanim_limitleri = limitleri_yukle()


class IhbarState:
  ONAY = 0
  KURUM = 1
  ADRES = 2
  DETAY = 3


def limit_kontrol(user_id):
  str_user_id = str(user_id)
  bugun = datetime.datetime.now().strftime("%Y-%m-%d")
  if str_user_id not in kullanim_limitleri:
    kullanim_limitleri[str_user_id] = {"tarih": bugun, "kullanim": 0}
  if kullanim_limitleri[str_user_id]["tarih"] != bugun:
    kullanim_limitleri[str_user_id] = {"tarih": bugun, "kullanim": 0}
  limitleri_kaydet(kullanim_limitleri)
  return kullanim_limitleri[str_user_id]["kullanim"] < GUNLUK_LIMIT


def check_all_memberships(user_id):
  for kanal in ZORUNLU_KANALLAR:
    try:
      member = bot.get_chat_member(kanal, user_id)
      print(f"[KONTROL] {kanal} - Kullanıcı Durumu: {member.status}")
      if member.status not in ["creator", "administrator", "member"]:
        return False
    except Exception as e:
      print(f"[UYARI] {kanal} kontrol edilirken hata: {e}")
      return False
  return True


@bot.message_handler(commands=["start"])
def send_welcome(message):
  if message.chat.type != "private":
    return

  user_id = message.chat.id
  print(f"\n[GELEN MESAJ] /start tıklandı! ID: {user_id}")

  try:
    if not check_all_memberships(user_id):
      markup = types.InlineKeyboardMarkup(row_width=1)
      for idx, kanal in enumerate(ZORUNLU_KANALLAR, start=1):
        clean_username = kanal.replace("@", "")
        btn_kanal = types.InlineKeyboardButton(
            f"📢 Zorunlu Kanal {idx} ({kanal})",
            url=f"https://t.me/{clean_username}",
        )
        markup.add(btn_kanal)

      btn_kontrol = types.InlineKeyboardButton(
          "🔄 Katıldım, Kontrol Et", callback_data="check_join"
      )
      markup.add(btn_kontrol)

      bot.send_message(
          user_id,
          "⛔ **Botu kullanabilmek için aşağıdaki zorunlu kanallara"
          " katılmalısınız!**",
          reply_markup=markup,
          parse_mode="Markdown",
      )
      return

    show_disclaimer(user_id)
  except Exception as e:
    print(f"[HATA MESAJI] /start işlenirken hata: {e}")


def show_disclaimer(user_id):
  markup = types.InlineKeyboardMarkup(row_width=1)
  btn_kabul = types.InlineKeyboardButton(
      "✅ Kabul Ediyorum", callback_data="kabul_et"
  )
  markup.add(btn_kabul)

  bot.send_message(
      user_id,
      f"⚠️ **UYARI VE SORUMLULUK REDDİ**\n\n👑 **Kurucu:**"
      f" {KURUCU}\n\n*Bu botun kullanımı sonucu"
      " doğabilecek herhangi bir yasal veya hukuki durumdan bot"
      " sahibi/yöneticileri sorumlu tutulamaz. Tüm sorumluluk kullanıcıya"
      " aittir.*\n\nDevam ederek şartları kabul etmiş olursunuz.",
      reply_markup=markup,
      parse_mode="Markdown",
  )


def show_kurumlar(user_id):
  if not limit_kontrol(user_id):
    bot.send_message(
        user_id,
        "❌ **Günlük ihbar limitiniz doldu!**\n\nHer kullanıcının günde 2"
        " hakkı vardır. Gece 00:00'da tekrar yenilenecektir.",
        parse_mode="Markdown",
    )
    return

  str_user_id = str(user_id)
  kalan_hak = GUNLUK_LIMIT - kullanim_limitleri[str_user_id]["kullanim"]

  markup = types.InlineKeyboardMarkup(row_width=2)
  markup.add(
      types.InlineKeyboardButton(
          "👮‍♂️ Polis", callback_data="kurum_Polis"
      ),
      types.InlineKeyboardButton(
          "🛡 Jandarma", callback_data="kurum_Jandarma"
      ),
      types.InlineKeyboardButton(
          "🚑 Ambulans", callback_data="kurum_Ambulans"
      ),
      types.InlineKeyboardButton(
          "🚒 İtfaiye", callback_data="kurum_Itfaiye"
      ),
  )

  bot.send_message(
      user_id,
      f"🚨 **İhbar Menüsü**\n👑 Kurucu: {KURUCU}\n📊 Kalan Hakkınız:"
      f" {kalan_hak}\n\nLütfen kurumu seçin:",
      reply_markup=markup,
      parse_mode="Markdown",'
  )


@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
  user_id = call.message.chat.id
  data = call.data

  try:
    bot.answer_callback_query(call.id)
  except Exception:
    pass

  if data == "check_join":
    if check_all_memberships(user_id):
      try:
        bot.delete_message(chat_id=user_id, message_id=call.message.message_id)
      except Exception:
        pass
      show_disclaimer(user_id)
    else:
      bot.send_message(
          user_id,
          "⚠️ Kanallara henüz katılmamışsınız! Lütfen tüm kanallara girip"
          " tekrar deneyin.",
      )

  elif data == "kabul_et":
    try:
      bot.delete_message(chat_id=user_id, message_id=call.message.message_id)
    except Exception:
      pass
    show_kurumlar(user_id)

  elif data.startswith("kurum_"):
    if not limit_kontrol(user_id):
      bot.send_message(user_id, "❌ Günlük hakkınız bitti!")
      return

    kurum = data.split("_")[1]
    user_data[user_id] = {"kurum": kurum, "step": IhbarState.ADRES}

    bot.send_message(
        user_id,
        f"📍 Seçilen Kurum: **{kurum}**\n\nLütfen olayın gerçekleştiği"
        " **adresi** yazın:",
        parse_mode="Markdown",
    )


@bot.message_handler(
    func=lambda message: message.chat.type == "private"
    and not message.text.startswith("/")
)
def handle_message(message):
  user_id = message.chat.id

  if user_id not in user_data:
    bot.send_message(user_id, "Lütfen işlemi başlatmak için /start yazın.")
    return

  state = user_data[user_id].get("step")

  if state == IhbarState.ADRES:
    user_data[user_id]["adres"] = message.text
    user_data[user_id]["step"] = IhbarState.DETAY
    bot.send_message(
        user_id,
        "📝 Adres alındı.\nŞimdi lütfen **olay detayını** yazın:",
        parse_mode="Markdown",
    )

  elif state == IhbarState.DETAY:
    user_data[user_id]["detay"] = message.text
    kurum = user_data[user_id]["kurum"]
    adres = user_data[user_id]["adres"]
    detay = message.text

    str_user_id = str(user_id)
    kullanim_limitleri[str_user_id]["kullanim"] += 1
    limitleri_kaydet(kullanim_limitleri)

    kalan = GUNLUK_LIMIT - kullanim_limitleri[str_user_id]["kullanim"]

    summary_msg = bot.send_message(
        user_id,
        f"📋 **İhbar Özeti:**\n- Kurum: {kurum}\n- Adres: {adres}\n- Detay:"
        f" {detay}\n\n⏳ **İhbar gönderiliyor...**",
        parse_mode="Markdown",
    )

    time.sleep(15)

    bot.edit_message_text(
        chat_id=user_id,
        message_id=summary_msg.message_id,
        text=(
            f"✅ **İHBAR BAŞARILI!**\n\nBugünlük kalan hakkınız:"
            f" {kalan}\n👑 Kurucu: {KURUCU}"
        ),
        parse_mode="Markdown",
    )

    del user_id[user_id] if user_id in user_data else None


# --- BOTU VE SUNUCUYU BAŞLATMA ---
if __name__ == "__main__":
  # Flask web sunucusunu arka planda başlatıyoruz
  t = threading.Thread(target=run_web)
  t.daemon = True
  t.start()

  print("🚀 BOT VE WEB SUNUCUSU BULUTTA BAŞLATILDI...")

  while True:
    try:
      bot.polling(none_stop=True, interval=1, timeout=60)
    except Exception as e:
      print(f"[BAĞLANTI KOPTU] Tekrar bağlanılıyor: {e}")
      time.sleep(3)
