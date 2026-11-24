# MDS FIFA Predictor - Telegram bot
# Installation: pip install python-telegram-bot==21.10
# Lancer: définir BOT_TOKEN puis python bot.py
import os, math
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

def poisson(k, lam):
    return math.exp(-lam) * lam**k / math.factorial(k)

def analyze(scores):
    # scores = [(home_goals, away_goals), ...], newest first
    weights = [5, 4, 3, 2, 1]
    def avg(values):
        return sum(v*w for v, w in zip(values, weights)) / sum(weights)
    home_for = avg([h for h, a in scores])
    away_for = avg([a for h, a in scores])
    lam_h = max(.15, (home_for + away_for) / 2)
    lam_a = max(.15, (away_for + home_for) / 2)
    home = draw = away = over15 = over25 = under35 = btts = 0
    best = (0, 0, -1)
    for h in range(11):
        for a in range(11):
            p = poisson(h, lam_h) * poisson(a, lam_a)
            if h > a: home += p
            elif h == a: draw += p
            else: away += p
            if h+a >= 2: over15 += p
            if h+a >= 3: over25 += p
            if h+a <= 3: under35 += p
            if h > 0 and a > 0: btts += p
            if p > best[2]: best = (h, a, p)
    return (home, draw, away, over15, over25, under35, btts, best, lam_h, lam_a)

def fmt(p): return f"{p*100:.1f}%"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "⚽ MDS FIFA PREDICTOR\\n"
        "Envoie les 5 derniers scores, du plus récent au plus ancien, un par ligne.\\n"
        "Format : 3-2\\n3-1\\n1-1\\n2-0\\n0-2"
    )

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)

async def scores(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lines = [x.strip() for x in update.message.text.splitlines() if x.strip()]
    if len(lines) != 5:
        await update.message.reply_text("Il faut exactement 5 lignes, par exemple :\\n3-2\\n3-1\\n1-1\\n2-0\\n0-2")
        return
    parsed = []
    try:
        for line in lines:
            parts = line.replace(":", "-").split("-")
            if len(parts) != 2: raise ValueError()
            h, a = int(parts[0].strip()), int(parts[1].strip())
            if not (0 <= h <= 30 and 0 <= a <= 30): raise ValueError()
            parsed.append((h, a))
    except ValueError:
        await update.message.reply_text("Format incorrect. Utilise deux nombres entiers par ligne, ex. 2-1.")
        return
    home, draw, away, o15, o25, u35, btts, best, lh, la = analyze(parsed)
    text = (
        "📊 MDS FIFA PREDICTOR\\n\\n"
        f"Score exact le plus probable : {best[0]} – {best[1]}\\n"
        f"Buts attendus : {lh+la:.2f}\\n\\n"
        "1X2\\n"
        f"1 (domicile) : {fmt(home)}\\nX (nul) : {fmt(draw)}\\n2 (extérieur) : {fmt(away)}\\n\\n"
        "Marchés de buts\\n"
        f"+1,5 : {fmt(o15)}\\n+2,5 : {fmt(o25)}\\n-3,5 : {fmt(u35)}\\nBTTS Oui : {fmt(btts)}\\n\\n"
        "⚠️ Estimations statistiques simplifiées, sans garantie. Les cinq scores ne suffisent pas à prédire sûrement un match."
    )
    await update.message.reply_text(text)

def main():
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise SystemExit("Ajoute ton token Telegram dans la variable d'environnement BOT_TOKEN.")
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, scores))
    app.run_polling()

if __name__ == "__main__":
    main()
