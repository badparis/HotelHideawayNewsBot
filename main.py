import discord
from discord.ext import commands
import requests
import os
import re
from datetime import datetime
from io import StringIO
os.environ['OPENBLAS_NUM_THREADS'] = '1'
import pandas as pd 
from changes import find_removed, looks_like_a_partial_download

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = 1444410472928379073 

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
    'SkinColor': 'https://languages.hotelhideawaythegame.com/gamedata/external_texts/SkinColor/en/0',
    'Pet': 'https://languages.hotelhideawaythegame.com/gamedata/external_texts/Pet/en/0',
    'Achievement': 'https://languages.hotelhideawaythegame.com/gamedata/external_texts/Achievement/en/0',
    'CarpenterCollection': 'https://languages.hotelhideawaythegame.com/gamedata/external_texts/CarpenterCollection/en/0',
    'ClothingSet': 'https://languages.hotelhideawaythegame.com/gamedata/external_texts/ClothingSet/en/0',
    'Color': 'https://languages.hotelhideawaythegame.com/gamedata/external_texts/Color/en/0',
    'Event': 'https://languages.hotelhideawaythegame.com/gamedata/external_texts/Event/en/0',
    'Inbox': 'https://languages.hotelhideawaythegame.com/gamedata/external_texts/Inbox/en/0',
    'LanguageCode': 'https://languages.hotelhideawaythegame.com/gamedata/external_texts/LanguageCode/en/0',
    'Layout': 'https://languages.hotelhideawaythegame.com/gamedata/external_texts/Layout/en/0',
    'NPC': 'https://languages.hotelhideawaythegame.com/gamedata/external_texts/NPC/en/0',
    'NewsAmbassadors': 'https://languages.hotelhideawaythegame.com/gamedata/external_texts/NewsAmbassadors/en/0',
    'Pattern': 'https://languages.hotelhideawaythegame.com/gamedata/external_texts/Pattern/en/0',
    'GDPR': 'https://languages.hotelhideawaythegame.com/gamedata/external_texts/GDPR/en/0',
    'RoomLayout': 'https://languages.hotelhideawaythegame.com/gamedata/external_texts/RoomLayout/en/0',
    'Sticker': 'https://languages.hotelhideawaythegame.com/gamedata/external_texts/Sticker/en/0',
    'Task': 'https://languages.hotelhideawaythegame.com/gamedata/external_texts/Task/en/0',
    'Pin': 'https://languages.hotelhideawaythegame.com/gamedata/external_texts/Pin/en/0',
    'DecorDash': 'https://languages.hotelhideawaythegame.com/gamedata/external_texts/DecorDash/en/0',
    'FishingClub': 'https://languages.hotelhideawaythegame.com/gamedata/external_texts/FishingClub/en/0'
}

HASHES_URL = 'https://languages.hotelhideawaythegame.com/gamedata/hashes'
CATEGORIES_CACHE = 'Categories_cache.csv'
ITEM_CATEGORY = re.compile(r'\d{4}[A-Z]|^(Back|Body|Face|Feet|Head|Legs)[FMU][A-Z0-9]|^Skin[A-Z]|^NPCDialogue|ProfileCard$')
ANNOUNCE_ON_FIRST_RUN = {'FishingClub'}

CACHE_FILES = {name: f"{name}_cache.csv" for name in DATA_FEEDS}

FEED_COLORS = {
    'Cloth': 0xEB459E, 'ClothingEffect': 0xEB459E, 'ClothingSet': 0xEB459E, 'FacePart': 0xEB459E, 'SkinColor': 0xEB459E,
    'Color': 0xFEE75C, 'Pattern': 0xFEE75C,
    'Furni': 0x3498DB, 'CarpenterCollection': 0x3498DB, 'DecorDash': 0x3498DB, 'Layout': 0x3498DB, 'RoomLayout': 0x3498DB,
    'Pet': 0xE67E22, 'Pin': 0x9B59B6, 'Sticker': 0x9B59B6, 'Achievement': 0x9B59B6, 'ProfileBackground': 0x1ABC9C,
    'Gesture': 0x57F287, 'Event': 0xF1C40F, 'Quests': 0xF1C40F, 'Task': 0xF1C40F, 'FishingClub': 0x1ABC9C,
}
DEFAULT_COLOR = 0x57F287

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

async def check_categories(channel):
    try:
        response = requests.get(HASHES_URL, timeout=10)
        response.raise_for_status()

        current = sorted({
            entry['category']
            for locale in response.json() if locale['locale']['Language'] == 'en'
            for entry in locale['hashes']
            if not ITEM_CATEGORY.search(entry['category'])
        })

        if not current:
            return

        known = set()
        if os.path.exists(CATEGORIES_CACHE):
            known = set(pd.read_csv(CATEGORIES_CACHE, keep_default_na=False)['Category'].astype(str))

        if known:
            for category in [c for c in current if c not in known]:
                embed = discord.Embed(color=discord.Color.gold(), timestamp=discord.utils.utcnow())
                embed.set_footer(text="Hideaway Report · nouvelle catégorie")
                embed.add_field(name="Nouvelle catégorie de textes:", value=category, inline=False)
                embed.add_field(name="Contenu (en):", value=f"https://languages.hotelhideawaythegame.com/gamedata/external_texts/{category}/en/0", inline=False)
                await channel.send(embed=embed)
                print(f"   -> Nouvelle catégorie signalée: {category}")

        pd.DataFrame({'Category': sorted(known | set(current))}).to_csv(CATEGORIES_CACHE, index=False)

    except Exception as e:
        print(f"ECHEC: vérification des catégories. {e}")

@bot.event
async def on_ready():
    print('We have logged in as {0.user}'.format(bot))
    print("\n--- DEDUT DU CYCLE DE VERIFICATION (CSV) ---")

    channel = bot.get_channel(int(CHANNEL_ID))
    if channel is None:
        print(f"AVERTISSEMENT : Canal ID {CHANNEL_ID} introuvable. Passage au cycle suivant.")
        await bot.close()
        return

    for name, url in DATA_FEEDS.items():
        cache_file = CACHE_FILES[name]

        try:
            print(f"--- VERIFICATION DE : {name} ({url}) ---")
            response = requests.get(url, timeout=10)
            response.raise_for_status()

            current_data_string = response.text.strip()
            df_current = pd.read_csv(StringIO(current_data_string), on_bad_lines='skip')

            df_cache = pd.DataFrame()
            if os.path.exists(cache_file):
                df_cache = pd.read_csv(cache_file)

            if df_cache.empty and name not in ANNOUNCE_ON_FIRST_RUN:
                print(f"Initialisation du flux {name}... ({len(df_current)} elements)")
            else:
                new_items = df_current if df_cache.empty else df_current[~df_current['Key'].isin(df_cache['Key'])]

                if not new_items.empty:
                    print(f"NOUVELLES DONNEES dans {name} : {len(new_items)} elements.")

                    await channel.send(f"--- 📣 **{len(new_items)} Nouveaux Codes Détectés dans {name.upper()} !** ---")
                    for index, row in new_items.iterrows():
                        key_value = row['Key']
                        name_value = row['English [en]']

                        embed = discord.Embed(color=FEED_COLORS.get(name, DEFAULT_COLOR), timestamp=discord.utils.utcnow())
                        embed.set_footer(text=f"Hideaway Report · {name}")
                        embed.add_field(name=f"New {name} key:", value=str(key_value)[:1024], inline=False)
                        embed.add_field(name="Nom (en):", value=str(name_value)[:1024] or '-', inline=False)

                        await channel.send(embed=embed)
                        print(f"   -> Message envoyé pour la clé: {key_value}")
                else:
                    print(f"Pas de nouveauté dans le flux {name}.")

            if not df_cache.empty:
                try:
                    removed = find_removed(
                        list(zip(df_cache['Key'], df_cache['English [en]'])),
                        set(df_current['Key']),
                        list(zip(new_items['Key'], new_items['English [en]'])),
                    )

                    if looks_like_a_partial_download(len(df_cache), len(removed)):
                        print(f"ALERTE: {len(removed)} cles absentes dans {name} : telechargement probablement partiel, cache conserve.")
                        continue

                    if removed:
                        await channel.send(f"--- 🗑️ **{len(removed)} Codes Retirés dans {name.upper()} !** ---")
                        for old_key, old_name, replacement in removed[:25]:
                            embed = discord.Embed(color=discord.Color.red(), timestamp=discord.utils.utcnow())
                            embed.set_footer(text=f"Hideaway Report · {name} · retiré")
                            embed.add_field(name=f"Removed {name} key:", value=old_key, inline=False)
                            embed.add_field(name="Nom (en):", value=str(old_name)[:1024] or "-", inline=False)
                            if replacement:
                                embed.add_field(name="Remplacé par:", value=replacement, inline=False)
                            await channel.send(embed=embed)
                        if len(removed) > 25:
                            await channel.send(f"… et {len(removed) - 25} autres codes retirés dans {name.upper()}.")
                except Exception as e:
                    print(f"ECHEC: annonce des codes retires pour {name}. {e}")

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

    await check_categories(channel)

    print("--- CYCLE DE VERIFICATION TERMINE ---")
    await bot.close()

if __name__ == '__main__':
    if not DISCORD_TOKEN:
        print("ERREUR: Le DISCORD_TOKEN n'a pas été trouvé. Assurez-vous qu'il est défini dans la configuration Systemd.")
    else:
        print("Starting main")
        bot.run(DISCORD_TOKEN)


