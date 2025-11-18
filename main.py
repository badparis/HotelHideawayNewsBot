import discord
from discord.ext import tasks, commands
import requests
import json
import os
import time

# --- Configuration ---
# Récupérer le token Discord depuis les Secrets Replit
DISCORD_TOKEN = os.environ.get('DISCORD_TOKEN')
URL_NEWS = 'https://languages.hotelhideawaythegame.com/gamedata/external_texts/NewsItem/en/0'
# REMPLACER CECI par l'ID réel du canal où le bot doit poster les nouvelles
CHANNEL_ID = 1440468437267910879  # <<< IMPORTANT

# Configuration des Intents (nécessaire pour la plupart des bots modernes)
intents = discord.Intents.default()
# intents.message_content = True # Activer si vous avez des commandes

# --- Bot Class ---


class NewsBot(commands.Bot):

    def __init__(self):
        # Configuration des commandes et des intents
        super().__init__(command_prefix='!', intents=intents)
        self.last_known_ids = set(
        )  # Utilisation d'un set pour une comparaison rapide
        self.channel_id = CHANNEL_ID

    def fetch_news(self):
        """Récupère les données JSON de l'URL."""
        try:
            response = requests.get(
                URL_NEWS, timeout=15)  # Timeout pour éviter les blocages
            response.raise_for_status(
            )  # Lève une exception si le statut n'est pas 200 (OK)
            return response.json()
        except requests.RequestException as e:
            print(
                f"[{time.strftime('%H:%M:%S')}] Erreur lors de la récupération de l'URL: {e}"
            )
            return None
        except json.JSONDecodeError:
            print(f"[{time.strftime('%H:%M:%S')}] Erreur de décodage JSON.")
            return None

    @tasks.loop(minutes=15)  # Le bot vérifie toutes les 15 minutes
    async def check_news(self):
        new_data = self.fetch_news()

        if new_data is None or not isinstance(new_data, list):
            return

        # 1. Identifier les IDs actuels. Chaque "NewsItem" a une clé "ID".
        current_ids = {item.get('ID') for item in new_data if item.get('ID')}

        if not self.last_known_ids:
            # 2. Première exécution : Initialiser sans notification
            self.last_known_ids = current_ids
            print(
                f"[{time.strftime('%H:%M:%S')}] Initialisation des {len(current_ids)} IDs de nouvelles réussie."
            )
            return

        # 3. Comparer : trouver les nouvelles IDs
        new_news_ids = current_ids - self.last_known_ids

        if new_news_ids:
            print(
                f"[{time.strftime('%H:%M:%S')}] {len(new_news_ids)} nouvelle(s) entrée(s) détectée(s)!"
            )
            channel = self.get_channel(self.channel_id)

            if channel:
                # 4. Notifier : Construire et envoyer le message

                # Filtrer pour avoir les objets complets des nouvelles entrées
                new_entries = [
                    item for item in new_data if item.get('ID') in new_news_ids
                ]

                for entry in new_entries:
                    # Le JSON contient "Title" et "Text".
                    title = entry.get('Title', 'Nouvelle entrée sans titre')
                    text_content = entry.get('Text', 'Contenu non disponible.')

                    # Nettoyage et formatage du contenu pour Discord
                    # On retire les retours à la ligne multiples et on tronque le message
                    clean_text = ' '.join(text_content.split()).replace(
                        '  ', ' ')

                    embed = discord.Embed(title=f"🚨 NOUVELLE NEWS : {title}",
                                          description=clean_text,
                                          color=discord.Color.red())

                    # Optionnel: Si vous voulez ajouter l'ID
                    # embed.set_footer(text=f"ID: {entry.get('ID')}")

                    await channel.send(embed=embed)

                # 5. Mettre à jour l'état
                self.last_known_ids = current_ids
            else:
                print(
                    f"[{time.strftime('%H:%M:%S')}] ATTENTION: Le canal ID {self.channel_id} est introuvable."
                )
        else:
            print(
                f"[{time.strftime('%H:%M:%S')}] Aucune nouvelle ligne détectée. ({len(current_ids)} IDs)"
            )

    @check_news.before_loop
    async def before_check_news(self):
        await self.wait_until_ready()
        print("Bot prêt. En attente du début de la vérification...")


# --- Lancement du Bot ---

if __name__ == "__main__":
    if DISCORD_TOKEN is None:
        print(
            "Erreur: Le token DISCORD_TOKEN n'est pas défini dans les Secrets Replit."
        )
    else:
        bot = NewsBot()
        try:
            bot.run(DISCORD_TOKEN)
        except discord.LoginFailure:
            print(
                "Erreur: Le Token Discord est invalide. Vérifiez vos Secrets Replit."
            )
        except Exception as e:
            print(f"Une erreur inattendue est survenue: {e}")
