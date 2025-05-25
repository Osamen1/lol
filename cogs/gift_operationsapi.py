import aiohttp
import json
import sqlite3
import ssl
import traceback

class GiftOperationsAPI:
    def __init__(self, api_url, api_key, db_path):
        self.api_url = api_url
        self.api_key = api_key
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        self.ssl_context = ssl.create_default_context()

    async def sync_with_api(self):
        try:
            self.cursor.execute("SELECT giftcode, date FROM gift_codes")
            db_codes = {row[0]: row[1] for row in self.cursor.fetchall()}
            
            connector = aiohttp.TCPConnector(ssl=self.ssl_context)
            async with aiohttp.ClientSession(connector=connector) as session:
                headers = {
                    'X-API-Key': self.api_key,
                    'Content-Type': 'application/json'
                }
                
                async with session.get(self.api_url, headers=headers) as response:
                    response_text = await response.text()
                    
                    if response.status == 200:
                        if not response_text:
                            print("API response is empty!")
                            return False
                        try:
                            result = json.loads(response_text)
                        except Exception as e:
                            print("API nie zwróciło poprawnego JSON:", e)
                            print("Treść odpowiedzi:", response_text)
                            return False

                        if 'error' in result:
                            return False

                        api_giftcodes = result.get('codes', [])
                        
                        # --- Twoja logika synchronizacji gift code'ów tutaj ---
                        # Np.: dodawanie/usuwanie kodów w lokalnej bazie na podstawie API
                        # Możesz zostawić swój kod z poprzedniej wersji
                        # ...

        except Exception as e:
            traceback.print_exc()

    async def remove_giftcode(self, giftcode: str, from_validation: bool = False) -> bool:
        try:
            if not from_validation:
                return False

            connector = aiohttp.TCPConnector(ssl=self.ssl_context)
            async with aiohttp.ClientSession(connector=connector) as session:
                headers = {
                    'Content-Type': 'application/json',
                    'X-API-Key': self.api_key
                }
                data = {'code': giftcode}
                
                async with session.delete(self.api_url, json=data, headers=headers) as response:
                    response_text = await response.text()
                    
                    if response.status == 200:
                        if not response_text:
                            print("API response is empty!")
                            return False
                        try:
                            result = json.loads(response_text)
                        except Exception as e:
                            print("API nie zwróciło poprawnego JSON:", e)
                            print("Treść odpowiedzi:", response_text)
                            return False

                        success = 'success' in result
                        if success:
                            self.cursor.execute("DELETE FROM gift_codes WHERE giftcode = ?", (giftcode,))
                            self.cursor.execute("DELETE FROM user_giftcodes WHERE giftcode = ?", (giftcode,))
                            self.conn.commit()
                        else:
                            return False
                        return success
                    else:
                        print(f"Błąd HTTP {response.status}")
                        print("Treść odpowiedzi:", response_text)
                        return False
        except Exception as e:
            traceback.print_exc()
            return False
