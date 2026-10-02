import os
import staypresent

if __name__ == "__main__":
    # Koyeb tomonidan beriladigan portni o'qish
    port = int(os.getenv("PORT", 8080))

    staypresent.run("bot.py", port=port)