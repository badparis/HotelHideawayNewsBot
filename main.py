import discord
from discord.ext import tasks, commands
import requests
import os
import time
import pandas as pd
import io

# --- Configuration Globale ---

DISCORD_TOKEN = os.environ.get('DISCORD_TOKEN')

# Dictionnaire des URLs à surveiller : {'Nom_du_flux': 'URL_du_flux'}
MONITORED_URLS = {
    'NewsItem':
    'https://languages.hotelhideawaythegame.com/gamedata/external_texts/NewsItem/en/0',
    'Cloth':
    'https://languages.hotelhideawaythegame.com/gamedata/external_texts/Cloth/en/0',
    'UI':
    'https://languages.hotelhideawaythegame.com/gamedata/external_texts/UI/en/0'
}

# ID du canal Discord
CHANNEL_ID = 1440468437267910879

# Configuration des Intents
intents = discord.Intents.default()

# --- Bot Class ---


class NewsBot(commands.Bot):

    def __init__(self):
        super().__init__(command_prefix='!', intents=intents)
        # last_known_ids devient un dictionnaire pour stocker l'état de CHAQUE flux
        self.last_known_ids = {}
        self.channel_id = CHANNEL_ID

    # Lance la tâche de fond dès que le bot est connecté et prêt.
    async def on_ready(self):
        print("✅ STATUT : Le bot est connecté à Discord et en ligne.")
        print(
            f"Lancement de la tâche de vérification (toutes les {self.check_news.minutes} minutes)..."
        )
        if not self.check_news.is_running():
            self.check_news.start()

    def fetch_news_data(self, url):
        """
        Récupère les données CSV de l'URL passée, les analyse avec Pandas et les
        convertit en liste de dictionnaires.
        """
        try:
            print(
                f"[{time.strftime('%H:%M:%S')}] Tentative de récupération...")

            headers = {
                'User-Agent':
                'Mozilla/5.0 (compatible; HotelHideawayNewsBot/1.0)'
            }
            # Utilise l'URL passée en argument
            response = requests.get(url, headers=headers, timeout=15)

            print(
                f"[{time.strftime('%H:%M:%S')}] SUCCÈS: Code de statut HTTP reçu: {response.status_code}"
            )

            response.raise_for_status()

            # --- LOGIQUE D'ANALYSE CSV AVEC PANDAS ---
            df = pd.read_csv(io.StringIO(response.text))

            # Renomme les colonnes : Key -> ID, English [en] -> Text (pour la logique suivante)
            df = df.rename(columns={'English [en]': 'Text', 'Key': 'ID'})

            # Convertit en une liste de dictionnaires
            return df.to_dict('records')
            # ----------------------------------------

        except requests.RequestException as e:
            print(
                f"[{time.strftime('%H:%M:%S')}] ÉCHEC: Erreur lors de la récupération de l'URL: {e}"
            )
            return None
        except Exception as e:
            print(
                f"[{time.strftime('%H:%M:%S')}] ÉCHEC DE L'ANALYSE DES DONNÉES: {e}"
            )
            return None

    @tasks.loop(minutes=15)  # Intervalle réglé à 15 minutes
    async def check_news(self):

        # Boucle sur tous les flux définis dans MONITORED_URLS
        for feed_name, url in MONITORED_URLS.items():
            print(
                f"\n[{time.strftime('%H:%M:%S')}] --- VÉRIFICATION DE : {feed_name} ---"
            )

            # Récupère les données du flux actuel
            new_data = self.fetch_news_data(url)

            # Ignore le flux si la récupération ou l'analyse a échoué
            if new_data is None or not isinstance(new_data, list):
                continue

            # 1. Identifier les IDs actuels.
            current_ids = {
                item.get('ID')
                for item in new_data if item.get('ID')
            }

            # --- Initialisation (première exécution pour CE flux) ---
            if feed_name not in self.last_known_ids:
                # Stocke l'ensemble des IDs pour ce flux
                self.last_known_ids[feed_name] = current_ids
                print(
                    f"[{time.strftime('%H:%M:%S')}] Initialisation du flux {feed_name} avec {len(current_ids)} IDs réussie."
                )
                continue

            # --- Comparaison ---
            # Trouve les IDs qui sont dans current_ids mais PAS dans last_known_ids[feed_name]
            new_news_ids = current_ids - self.last_known_ids[feed_name]

            if new_news_ids:
                print(
                    f"[{time.strftime('%H:%M:%S')}] {len(new_news_ids)} nouvelle(s) entrée(s) détectée(s) dans le flux {feed_name}!"
                )

                # 4. Préparation et envoi du message
                try:
                    channel = await self.fetch_channel(self.channel_id)
                except discord.NotFound:
                    print(
                        f"[{time.strftime('%H:%M:%S')}] ATTENTION: Le canal ID {self.channel_id} est introuvable sur Discord."
                    )
                    continue

                if not isinstance(channel,
                                  (discord.TextChannel, discord.DMChannel)):
                    print(
                        f"[{time.strftime('%H:%M:%S')}] ATTENTION: Le canal ID {self.channel_id} n'est pas un canal textuel. Envoi impossible."
                    )
                    continue

                new_entries = [
                    item for item in new_data if item.get('ID') in new_news_ids
                ]

                for entry in new_entries:
                    # Utilise la clé 'ID' (ex: NewsItem/2024...) pour le titre
                    title_key = entry.get('ID',
                                          'Entrée sans ID').split('/')[-1]
                    text_content = entry.get('Text', 'Contenu non disponible.')

                    clean_text = ' '.join(text_content.split()).replace(
                        '  ', ' ')

                    embed = discord.Embed(
                        # Afficher le nom du flux dans le titre est crucial pour la clarté
                        title=f"🚨 NOUVEAU ({feed_name}) : {title_key}",
                        description=clean_text[:1000] +
                        ("..." if len(clean_text) > 1000 else ""),
                        color=discord.Color.red())

                    await channel.send(embed=embed)

                # 5. Mettre à jour l'état pour CE flux
                self.last_known_ids[feed_name] = current_ids
            else:
                print(
                    f"[{time.strftime('%H:%M:%S')}] Aucune nouvelle ligne détectée dans {feed_name}. ({len(current_ids)} IDs)"
                )


# --- Lancement du Bot ---

if __name__ == "__main__":
    if DISCORD_TOKEN is None:
        print(
            "Erreur: Le token DISCORD_TOKEN n'est pas défini dans les Secrets Replit."
        )
    else:
        bot = NewsBot()
        try:
            # Assurez-vous que CHANNEL_ID est un entier
            try:
                bot.channel_id = int(bot.channel_id)
            except ValueError:
                print("Erreur: L'ID du canal doit être un nombre entier.")
                exit()

            bot.run(DISCORD_TOKEN)
        except discord.LoginFailure:
            print(
                "Erreur: Le Token Discord est invalide. Vérifiez vos Secrets Replit."
            )
        except Exception as e:
            print(f"Une erreur inattendue est survenue: {e}")
