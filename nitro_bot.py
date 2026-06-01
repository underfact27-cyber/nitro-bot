import asyncio
import json
import random
import string
import time
import tempfile
import discord
from discord import app_commands, Embed, ui, ButtonStyle
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import undetected_chromedriver as uc

# ================= CONFIG =================
SENTENCE = "The quick brown fox jumps over the lazy dog."
ACCOUNTS_FILE = "nitro_accounts.json"
LOG_CHANNEL_ID = 1510318331310247957
DETAILED_LOG_CHANNEL_ID = 1510663317641891851
ALLOWED_GENERATE_USERS = [1401756418897608714]

codes_db = {}

def create_driver():
    options = uc.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-dev-shm-usage")

    temp_dir = tempfile.mkdtemp()
    options.add_argument(f"--user-data-dir={temp_dir}")
    return uc.Chrome(options=options, version_main=148)

def random_string(length=10):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

def generate_code():
    return "NT-" + random_string(12).upper()

# ================= DISCORD SETUP =================
intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

# ================= REDEEM MODAL =================
class RedeemModal(ui.Modal, title="Redeem Code"):
    code = ui.TextInput(label="Code", placeholder="NT-XXXXXXXXXXXX", required=True)
    profile_url = ui.TextInput(label="Profile URL", placeholder="https://nitrotype.com/racer/username", required=True)
    add_friend = ui.TextInput(label="Add Friends? (T/F)", placeholder="T or F", required=True, max_length=1)

    async def on_submit(self, interaction: discord.Interaction):
        code = self.code.value.strip().upper()
        profile_url = self.profile_url.value.strip()
        add_friend = self.add_friend.value.strip().upper() == "T"

        if code not in codes_db or codes_db[code] <= 0:
            await interaction.response.send_message("❌ Invalid or expired code.", ephemeral=True)
            return

        views = codes_db[code]
        await interaction.response.send_message(f"✅ Code accepted! Running **{views}** views...", ephemeral=True)

        log_channel = client.get_channel(LOG_CHANNEL_ID)
        detailed_channel = client.get_channel(DETAILED_LOG_CHANNEL_ID)

        embed = Embed(title="🔑 Code Redemption", color=0x00ff00)
        embed.add_field(name="User", value=str(interaction.user), inline=False)
        embed.add_field(name="Code", value=f"`{code}`", inline=False)
        embed.add_field(name="Profile", value=profile_url, inline=False)
        embed.add_field(name="Add Friends", value="✅ Yes" if add_friend else "❌ No", inline=False)
        embed.add_field(name="Progress", value="Starting...", inline=False)
        embed.set_footer(text="by @xbhcufi")

        if log_channel:
            log_msg = await log_channel.send(embed=embed)

        for i in range(views):
            status = f"Account {i+1}/{views} - Starting..."
            if log_channel:
                embed.set_field_at(4, name="Progress", value=status)
                await log_msg.edit(embed=embed)

            await create_single_account(profile_url, add_friend, log_channel, detailed_channel)
            await asyncio.sleep(4)

        codes_db[code] = 0
        if log_channel:
            embed.set_field_at(4, name="Progress", value="✅ **Fully Completed**")
            await log_msg.edit(embed=embed)

# ================= PANEL =================
class PanelView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label="Redeem Code", style=ButtonStyle.green, custom_id="redeem_button")
    async def redeem_button(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(RedeemModal())

# ================= CREATE SINGLE ACCOUNT =================
async def create_single_account(target_profile_url, add_friend, log_channel, detailed_channel):
    driver = None
    try:
        driver = create_driver()
        if detailed_channel:
            await detailed_channel.send("opening chrome...")

        driver.get("https://nitrotype.com/race")
        await asyncio.sleep(10)  # Extra wait for page to load

        if detailed_channel:
            await detailed_channel.send("viewing race page")

        try:
            iframe = WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, "iframe")))
            driver.switch_to.frame(iframe)
        except:
            pass

        # Wait for race text to appear
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".race-text, .words, [class*='word']"))
            )
        except:
            pass

        driver.execute_script("document.body.click();")
        await asyncio.sleep(5)

        if detailed_channel:
            await detailed_channel.send("started typing")

        body = driver.find_element(By.TAG_NAME, "body")
        body.click()
        await asyncio.sleep(3)

        # RELIABLE TYPING - WORKS EVERY TIME
        for char in SENTENCE:
            body.send_keys(char)
            time.sleep(random.uniform(0.08, 0.12))  # Safe, reliable speed

        if detailed_channel:
            await detailed_channel.send("typing complete")

        await asyncio.sleep(8)

        if detailed_channel:
            await detailed_channel.send("filling signup")

        username = "nt" + random_string(8)
        password = random_string(12) + "A!"

        try:
            username_field = WebDriverWait(driver, 12).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='username'], #username"))
            )
            username_field.clear()
            username_field.send_keys(username)

            password_field = driver.find_element(By.CSS_SELECTOR, "input[name='password'], #password")
            password_field.clear()
            password_field.send_keys(password)

            submit_btn = WebDriverWait(driver, 8).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit'], .btn--primary"))
            )
            submit_btn.click()

            if detailed_channel:
                await detailed_channel.send("signup complete")

            await asyncio.sleep(8)
        except:
            if detailed_channel:
                await detailed_channel.send("signup error")

        driver.switch_to.default_content()

        if detailed_channel:
            await detailed_channel.send("viewing requested profile")

        driver.get(target_profile_url)
        await asyncio.sleep(12)

        if add_friend:
            if detailed_channel:
                await detailed_channel.send("👥 Adding friend...")

            friend_selectors = [
                "button.btn--primary",
                ".btn--primary",
                "button.btn--top.btn--primary",
                "button.btn--thinner",
                "button.add-friend",
                ".btn--friend",
                "[class*='add-friend']",
                "button[title*='Add Friend']",
                ".add-friend-btn"
            ]

            friend_added = False
            for selector in friend_selectors:
                try:
                    btn = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                    if "Add Friend" in btn.text or "adduser" in str(btn.get_attribute("innerHTML")):
                        btn.click()
                        friend_added = True
                        if detailed_channel:
                            await detailed_channel.send(f"✅ Friend added!")
                        break
                except:
                    continue

            if not friend_added and detailed_channel:
                await detailed_channel.send("⚠️ Add Friend button not found")

        if detailed_channel:
            await detailed_channel.send(f"✅ Finished → `{username}` viewed {target_profile_url}")

        if log_channel:
            await log_channel.send(f"✅ Finished → `{username}` viewed {target_profile_url}")

        return username

    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass

# ================= COMMANDS =================
@tree.command(name="panel", description="Show redeem panel")
async def panel(interaction: discord.Interaction):
    embed = Embed(title="Nitro Type View Bot", description="Click below to redeem a code", color=0x00ff00)
    embed.set_footer(text="by @xbhcufi")
    await interaction.response.send_message(embed=embed, view=PanelView())

@tree.command(name="generate", description="Generate redeem codes")
@app_commands.describe(views="Views per code", amount="How many codes")
async def generate(interaction: discord.Interaction, views: int, amount: int = 1):
    if interaction.user.id not in ALLOWED_GENERATE_USERS:
        await interaction.response.send_message("❌ You don't have permission.", ephemeral=True)
        return

    codes = []
    for _ in range(amount):
        code = generate_code()
        codes_db[code] = views
        codes.append(code)

    embed = Embed(title="✅ Codes Generated", color=0x00ff00)
    embed.add_field(name="Views per code", value=str(views), inline=False)
    embed.add_field(name="Codes", value="\n".join([f"`{c}`" for c in codes]), inline=False)
    embed.set_footer(text="by @xbhcufi")
    await interaction.response.send_message(embed=embed)

@client.event
async def on_ready():
    await tree.sync()
    print(f"✅ Bot Online: {client.user}")

if __name__ == "__main__":
    client.run("MTUxMDA4MjYzODkyNzYyNjI3MA.GBxe3J.MlUEabu1xQ5o9D_Uz2YGDer3YbUFIRmDuw4dA8")