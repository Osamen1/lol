import discord
from discord.ext import commands
import requests
import sqlite3

CHANNEL_NAME = "porozmawiaj-z-andrzejem"  # <-- wpisz nazwę swojego kanału
OPENROUTER_API_KEY = "usuwam na wypadek kradziezy"
HISTORY_LENGTH = 10

MODEL = "meta-llama/llama-4-maverick"  # Najbardziej realistyczny darmowy model na OpenRouter

class AIChat(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_path = "db/ai_histories.sqlite"

    def get_history(self, user_id, channel_name):
        history = [
            {"role": "system", "content":
                "Jesteś realistycznym polskim nastolatkiem (ok. 17 lat). Masz mnóstwo zainteresowań: gry komputerowe i planszowe, sport, muzyka, filmy, seriale, anime, programowanie, podróże, memy, gotowanie, motoryzacja, nauka, historia, technologia i wiele innych – możesz rozmawiać na każdy temat, a rozmowa z Tobą nigdy nie jest nudna. Mówisz młodzieżowym, swobodnym, naturalnym stylem, czasem wtrącasz potoczne zwroty i emotki (np. XD, git, spoko, ej, lol), ale nie przesadzasz – starasz się, by każda odpowiedź była autentyczna, luźna, ale nie karykaturalna. Gdy rozmowa schodzi na temat relacji, uczuć lub zakochania, stajesz się dobrym romantykiem: jesteś empatyczny, wrażliwy i wspierający, potrafisz okazać zrozumienie i napisać coś miłego lub dać poradę. Zawsze reagujesz tak, jak prawdziwy, otwarty i ogarnięty nastolatek z Discorda – czasem żartujesz, czasem jesteś poważny, zależnie od tonu rozmowy."
            }
        ]
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT role, content FROM ai_chat_history
                WHERE user_id = ? AND channel_name = ?
                ORDER BY id DESC
                LIMIT ?
            """, (user_id, channel_name, HISTORY_LENGTH*2))
            rows = cursor.fetchall()
            for row in reversed(rows):
                history.append({"role": row[0], "content": row[1]})
            conn.close()
        except Exception as e:
            print(f"Błąd pobierania historii AI: {e}")
        return history

    def save_message(self, user_id, channel_name, role, content):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO ai_chat_history (user_id, channel_name, role, content)
                VALUES (?, ?, ?, ?)
            """, (user_id, channel_name, role, content))
            conn.commit()
            cursor.execute("""
                SELECT id FROM ai_chat_history
                WHERE user_id = ? AND channel_name = ?
                ORDER BY id DESC
                LIMIT -1 OFFSET ?
            """, (user_id, channel_name, HISTORY_LENGTH*2))
            old_ids = cursor.fetchall()
            if old_ids:
                to_delete = [id[0] for id in old_ids]
                cursor.executemany("DELETE FROM ai_chat_history WHERE id = ?", [(i,) for i in to_delete])
                conn.commit()
            conn.close()
        except Exception as e:
            print(f"Błąd zapisu historii AI: {e}")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return
        if message.channel.name != CHANNEL_NAME:
            return
        if not message.content.strip():
            return

        user_id = message.author.id
        prompt = message.content.strip()
        channel_name = message.channel.name

        # Pobierz historię rozmowy z bazy
        history = self.get_history(user_id, channel_name)
        history.append({"role": "user", "content": prompt})

        await message.channel.typing()
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://discord.com"  # wymagany nagłówek!
        }
        data = {
            "model": MODEL,
            "messages": history,
            "max_tokens": 512,
            "temperature": 0.7
        }
        try:
            response = requests.post(url, headers=headers, json=data, timeout=45)
            if response.status_code == 200:
                ai_reply = response.json()["choices"][0]["message"]["content"]
                await message.reply(ai_reply, mention_author=False)
                self.save_message(user_id, channel_name, "user", prompt)
                self.save_message(user_id, channel_name, "assistant", ai_reply)
            else:
                print("\n[AI ERROR RESPONSE]", response.status_code, response.text, "\n")
                await message.reply("Wystąpił błąd przy komunikacji z AI.", mention_author=False)
        except Exception as e:
            await message.reply("Wystąpił błąd techniczny.", mention_author=False)
            print(f"Błąd AIChat: {e}")

async def setup(bot):
    await bot.add_cog(AIChat(bot))
