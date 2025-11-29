import discord
from discord.ext import tasks, commands
import requests
import os
from datetime import datetime
from io import StringIO
import pandas as pd 

# --- 1. CONFIGURATION ---

# Le token est chargé par Systemd.
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = 1440468437267910879 

# URLs des flux de données à surveiller (Format CSV)
# Ces flux seront vérifiés séquentiellement à chaque cycle.
DATA_FEEDS = {
    'NewsItem': 'https://languages.hotelhideawaythegame.com/gamedata/external_texts/NewsItem/en/0',
    'Cloth': 'https://languages.hotelhideawaythegame.com/gamedata/external_texts/Cloth/en/0',
    'UI': 'https://languages.hotelhideawaythegame.com/gamedata/external_texts/UI/en/0',
    'ClothingEffect': 'https://languages.hotelhideawaythegame.com/gamedata/external_texts/ClothingEffect/en/0',
    'FacePart': 'https://languages.hotelhideawaythegame.com/gamedata/external_texts/FacePart/en/0',
    'Furni': 'https://languages.hotelhideawaythegame.com/gamedata/external_texts/Furni/en/0',
    'Gesture': 'https://languages.hotelhideawaythegame.com/gamedata/external_texts/Gesture/en/0',
    'ProfileBackground': 'https://languages.hotelhideawaythegame.com/gamedata/external_texts/ProfileBackground/en/0',
    'Quests': 'https://languages.hotelhideawaythegame.com/gamedata/external_texts/quests/en/0',
    'SkinColor': 'https://languages.hotelhideawaythegame.com/gamedata/external_texts/SkinColor/en/0'
}

# Fichiers de cache (pour enregistrer l'état précédent en CSV)
CACHE_FILES = {name: f"{name}_cache.csv" for name in DATA_FEEDS}

# --- 2. CLASSE BOT PRINCIPALE ---

class NewsBot(commands.Bot):
    def __init__(self):
        # Activation des Intents nécessaires
        intents = discord.Intents.all() 
        intents.members = True 
        intents.presences = True 
        intents.message_content = True 

        super().__init__(command_prefix='!', intents=intents)
        self.is_ready = False 
        
    async def on_ready(self):
        if not self.is_ready:
            await self.start_tasks()
            self.is_ready = True

    async def start_tasks(self):
        print("✅ STATUT : Le bot est connecté à Discord et en ligne.")
        # Affichage de la fréquence actuelle (basée sur le décorateur @tasks.loop)
        print(f"Lancement de la tâche de vérification (toutes les {self.check_news.minutes} minutes)...") 
        
        if not self.check_news.is_running():
            self.check_news.start()

# --- 3. LOGIQUE DE TÂCHE DE FOND (Lecture CSV directe) ---
    
    # Fréquence de vérification (actuellement 55 minutes)
    @tasks.loop(minutes=55) 
    async def check_news(self):
        print("\n--- DÉBUT DU CYCLE DE VÉRIFICATION (CSV) ---")
        
        channel = self.get_channel(int(CHANNEL_ID)) 
        
        if channel is None:
            print(f"❌ AVERTISSEMENT : Canal ID {CHANNEL_ID} introuvable. Passage au cycle suivant.")
            return

        for name, url in DATA_FEEDS.items():
            cache_file = CACHE_FILES[name]
            
            try:
                print(f"--- VÉRIFICATION DE : {name} ({url}) ---")
                
                # 1. Récupération des données actuelles
                response = requests.get(url, timeout=10) 
                response.raise_for_status() 
                
                current_data_string = response.text.strip() # Contenu CSV brut
                
                # Lecture du CSV avec pandas
                df_current = pd.read_csv(StringIO(current_data_string))

                # 2. Charger les données en cache
                df_cache = pd.DataFrame()
                if os.path.exists(cache_file):
                    df_cache = pd.read_csv(cache_file)
                
                # 3. Comparaison et recherche de nouveaux éléments
                if df_cache.empty:
                    print(f"Initialisation du flux {name}... réussie. ({len(df_current)} éléments enregistrés)")
                    
                else:
                    # Trouver les nouvelles lignes qui ne sont pas dans le cache (comparaison sur la colonne 'Key')
                    new_items = df_current[~df_current['Key'].isin(df_cache['Key'])]
                    
                    if not new_items.empty:
                        print(f"🚨 NOUVELLES DONNÉES TROUVÉES dans {name} : {len(new_items)} éléments.")
                        
                        # Envoi d'un message d'introduction
                        await channel.send(f"--- 📣 **{len(new_items)} Nouveaux Codes Détectés dans {name.upper()} !** ---")

                        # 4. Traitement et envoi d'Embeds (correspondant à la maquette)
                        for index, row in new_items.iterrows():
                            key_value = row['Key']
                            # La colonne 'English [en]' contient le nom affichable
                            name_value = row['English [en]']
                            
                            embed = discord.Embed(
                                color=discord.Color.green(),
                            )
                            # Champ 1: New Cloth key: Cloth/Name/HeadU2508AstrologistVeil
                            embed.add_field(name=f"New {name} key:", value=key_value, inline=False)
                            # Champ 2: Arcane Astrologer's Veil
                            embed.add_field(name="Nom (en):", value=name_value, inline=False)
                            
                            await channel.send(embed=embed)
                            print(f"   -> Message envoyé pour la clé: {key_value}")
                    else:
                        print(f"Pas de nouveauté dans le flux {name}.")

                # 5. Mise à jour du cache
                df_current.to_csv(cache_file, index=False)
                
            except requests.exceptions.Timeout:
                print(f"ÉCHEC: Le délai d'attente (timeout) de 10 secondes a expiré pour {name}.")
            except requests.exceptions.RequestException as e:
                print(f"ÉCHEC: Erreur de requête pour {name}. {e}")
            except pd.errors.ParserError as e:
                 print(f"ÉCHEC: Erreur d'analyse CSV pour {name}. Le format est invalide ou incomplet. {e}")
            except KeyError as e:
                print(f"ÉCHEC: Colonne CSV manquante lors de la manipulation des données (Colonne non trouvée) : {e}")
            except Exception as e:
                print(f"ÉCHEC: Erreur inattendue lors de la vérification de {name}. {e}")
                
        print("--- CYCLE DE VÉRIFICATION TERMINÉ ---")

    @check_news.before_loop
    async def before_check_news(self):
        print("En attente de la connexion du bot avant le premier lancement...")
        await self.wait_until_ready()


# --- 4. LANCEMENT DU BOT ---

if __name__ == '__main__':
    if not DISCORD_TOKEN:
        print("ERREUR: Le DISCORD_TOKEN n'a pas été trouvé. Assurez-vous qu'il est défini dans la configuration Systemd.")
    else:
        bot = NewsBot()
        
        try:
            bot.run(DISCORD_TOKEN)
        except Exception as e:
            print(f"ERREUR CRITIQUE lors du lancement du bot : {e}")
