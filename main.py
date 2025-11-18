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

# >>> IMPORTANT : REMPLACER PAR L'ID RÉEL DE VOTRE CANAL DISCORD <<<
# J'utilise l'ID que vous avez fourni, assurez-vous qu'il est correct.
CHANNEL_ID = 1440468437267910879

# Configuration des Intents
intents = discord.Intents.default()

# --- Bot Class ---


class NewsBot(commands.Bot):

    def __init__(self):
        super().__init__(command_prefix='!', intents=intents)
        self.last_known_ids = set(
        )  # Utilisation d'un set pour une comparaison rapide
        self.channel_id = CHANNEL_ID

    # NOUVEAU : Lance la tâche de fond dès que le bot est connecté et prêt.
    async def on_ready(self):
        print("✅ STATUT : Le bot est connecté à Discord et en ligne.")
        print(
            f"Lancement de la tâche de vérification (toutes les {self.check_news.minutes} minutes)..."
        )
        if not self.check_news.is_running():
            self.check_news.start()

    def fetch_news_data(self):
        """Récupère les données JSON de l'URL."""
        try:
            print(
                f"[{time.strftime('%H:%M:%S')}] TENTATIVE: Envoi de la requête à l'URL des nouvelles..."
            )

            headers = {
                'User-Agent':
                'Mozilla/5.0 (compatible; HotelHideawayNewsBot/1.0)'
            }
            response = requests.get(URL_NEWS, headers=headers, timeout=15)

            print(
                f"[{time.strftime('%H:%M:%S')}] SUCCÈS: Code de statut HTTP reçu: {response.status_code}"
            )

            response.raise_for_status()

            # --- MODIFICATION CLÉ ICI ---
            try:
                # Essayer de décoder le JSON
                return response.json()
            except json.JSONDecodeError:
                # Si le décodage échoue, imprimer un message spécifique et retourner None
                print(
                    f"[{time.strftime('%H:%M:%S')}] ÉCHEC DÉCODAGE: Le contenu reçu n'est pas du JSON valide. Contenu: {response.text[:50]}..."
                )
                return None
            # -----------------------------

        except requests.RequestException as e:
            print(
                f"[{time.strftime('%H:%M:%S')}] ÉCHEC: Erreur lors de la récupération de l'URL: {e}"
            )
            return None

    @tasks.loop(
        minutes=1)  # TEMPORAIRE: Réglé sur 1 minute pour le test initial
    async def check_news(self):
        new_data = self.fetch_news_data()

        if new_data is None or not isinstance(new_data, list):
            return

        # 1. Identifier les IDs actuels.
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

            # --- CORRECTION DE CONNEXION AU CANAL ---
            try:
                # Utilisation de fetch_channel pour une connexion fiable au canal
                channel = await self.fetch_channel(self.channel_id)
            except discord.NotFound:
                print(
                    f"[{time.strftime('%H:%M:%S')}] ATTENTION: Le canal ID {self.channel_id} est introuvable sur Discord."
                )
                return

            # Vérification de type (assure que c'est un canal textuel ou DM)
            if not isinstance(channel,
                              (discord.TextChannel, discord.DMChannel)):
                print(
                    f"[{time.strftime('%H:%M:%S')}] ATTENTION: Le canal ID {self.channel_id} n'est pas un canal textuel. Envoi impossible."
                )
                return
            # ----------------------------------------

            # 4. Notifier : Construire et envoyer le message
            new_entries = [
                item for item in new_data if item.get('ID') in new_news_ids
            ]

            for entry in new_entries:
                title = entry.get('Title', 'Nouvelle entrée sans titre')
                text_content = entry.get('Text', 'Contenu non disponible.')

                # Nettoyage et formatage du contenu
                clean_text = ' '.join(text_content.split()).replace('  ', ' ')

                embed = discord.Embed(title=f"🚨 NOUVELLE NEWS : {title}",
                                      description=clean_text,
                                      color=discord.Color.red())

                await channel.send(embed=embed)

            # 5. Mettre à jour l'état
            self.last_known_ids = current_ids
        else:
            print(
                f"[{time.strftime('%H:%M:%S')}] Aucune nouvelle ligne détectée. ({len(current_ids)} IDs)"
            )


# REMARQUE : La fonction before_check_news est retirée pour débloquer le démarrage.

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
