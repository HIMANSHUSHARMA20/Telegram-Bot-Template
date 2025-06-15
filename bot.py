import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from datetime import datetime, timedelta

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


# You can get your own one bot from @BotFather on Telegram
bot_key = "YOUR_BOT_TOKEN_HERE" # Place your bot token here 


udetails = {}

async def go_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    udetails[uid] = {
        'super_mode': True,
        'mode_exp': datetime.now() + timedelta(days=3)
    }
    kbs = [[InlineKeyboardButton("Build My Profile", callback_data="start_prof")]]
    rm = InlineKeyboardMarkup(kbs)
    await update.message.reply_text(
        "Hello! Let's get your profile ready.\n"
        "You'll get a 3-day test of special features!",
        reply_markup=rm
    )

async def see_prof(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in udetails:
        await update.message.reply_text("You haven't made a profile yet. Use /start to do it.")
        return

    pdata = udetails[uid]
    stat = "🌟 Super Mode On" if pdata.get('super_mode') else "🔒 Super Mode Off"
    
    await update.message.reply_text(
        f"{stat}\n{show_prof_data(pdata)}",
        parse_mode="Markdown"
    )
    
    kbs = [
        [InlineKeyboardButton("Fix Profile", callback_data="fix_prof")],
    ]
    rm = InlineKeyboardMarkup(kbs)
    await update.message.reply_text("Manage your profile:", reply_markup=rm)


async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q_data = update.callback_query
    uid = q_data.from_user.id
    await q_data.answer()

    if q_data.data == "start_prof":
        await q_data.message.reply_text("What's your first name?")
        context.user_data["cur_step"] = "name_in"

    elif q_data.data == "fix_prof":
        await q_data.message.reply_text(
            "Pick what to change:",
            reply_markup=get_edit_menu(udetails[uid])
        )

    elif q_data.data.startswith("edit_"):
        fld = q_data.data.split("_")[1]
        context.user_data["edit_fld"] = {"fld": fld}
        
        if fld == "p_type":
            await q_data.message.reply_text(
                "Select your main type:",
                reply_markup=get_type_menu(udetails[uid].get("p_type"))
            )
        elif fld == "favs":
            await q_data.message.reply_text(
                "Pick your favs (max 5):",
                reply_markup=get_fav_menu(
                    udetails[uid].get("favs", []),
                    is_edit=True
                )
            )
        elif fld == "see_type":
            await q_data.message.reply_text(
                "What type of content do you like to see?",
                reply_markup=get_see_menu(
                    udetails[uid].get("see_type"))
            )
        else:
            await q_data.message.reply_text(f"Tell me your new {fld.replace('_', ' ')}:")

    elif q_data.data.startswith("type_"):
        cat = q_data.data.split("_")[1]
        if "cur_step" in context.user_data:
            udetails[uid]["p_type"] = cat
            await q_data.message.reply_text("Write a short bit about yourself:")
            context.user_data["cur_step"] = "desc_in"
        else:
            udetails[uid]["p_type"] = cat
            await q_data.edit_message_text("✅ Type updated!")
            await show_prof_and_opts(q_data.message, uid)
            context.user_data.clear()

    elif q_data.data.startswith("fav_"):
        item = q_data.data.split("_")[1]
        sel_list = context.user_data.get("picked_favs", [])
        
        if item in sel_list:
            sel_list.remove(item)
        elif len(sel_list) < 5:
            sel_list.append(item)
            
        context.user_data["picked_favs"] = sel_list
        
        if "cur_step" in context.user_data:
            await q_data.edit_message_reply_markup(
                get_fav_menu(sel_list, is_create=True)
            )
        else:
            await q_data.edit_message_reply_markup(
                get_fav_menu(sel_list, is_edit=True)
            )

    elif q_data.data == "ok_favs":
        fin_items = context.user_data.get("picked_favs", [])
        if not 1 <= len(fin_items) <= 5:
            await q_data.answer("Pick 1 to 5 favs", show_alert=True)
            return
            
        udetails[uid]["favs"] = fin_items
        
        if "cur_step" in context.user_data:
            await q_data.message.reply_text("What are your big goals?")
            context.user_data["cur_step"] = "goals_in"
        else:
            await q_data.message.reply_text("✅ Favs updated!")
            await show_prof_and_opts(q_data.message, uid)
            context.user_data.clear()

    elif q_data.data.startswith("see_"):
        pref = q_data.data.split("_")[1]
        if "cur_step" in context.user_data:
            udetails[uid]["see_type"] = pref
            await q_data.message.reply_text("Where are you from?")
            context.user_data["cur_step"] = "place_in"
        else:
            udetails[uid]["see_type"] = pref
            await q_data.edit_message_text("✅ See type updated!")
            await show_prof_and_opts(q_data.message, uid)
            context.user_data.clear()

    elif q_data.data == "finish_prof":
        await q_data.message.reply_text(
            "Profile done! You get 3 days of super mode.\n"
            f"{show_prof_data(udetails[uid])}",
            parse_mode="Markdown"
        )
        await show_prof_and_opts(q_data.message, uid)
        context.user_data.clear()


async def handle_text_in(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    txt_in = update.message.text
    
    if "cur_step" in context.user_data:
        step = context.user_data["cur_step"]
        
        if step == "name_in":
            udetails[uid]["my_name"] = txt_in
            await update.message.reply_text("How old are you?")
            context.user_data["cur_step"] = "age_in"
            
        elif step == "age_in":
            try:
                uage = int(txt_in)
                if not 10 <= uage <= 120:
                    await update.message.reply_text("Age must be 10-120.")
                    return
                udetails[uid]["age"] = uage
                await update.message.reply_text(
                    "What's your main type?",
                    reply_markup=get_type_menu()
                )
                context.user_data["cur_step"] = "type_sel"
            except ValueError:
                await update.message.reply_text("Please use numbers for age.")
                
        elif step == "desc_in":
            if len(txt_in) > 500:
                await update.message.reply_text("Description too long (max 500 chars).")
                return
            udetails[uid]["about_me"] = txt_in
            await update.message.reply_text(
                "Now, pick your favs (max 5):",
                reply_markup=get_fav_menu(is_create=True)
            )
            context.user_data["cur_step"] = "fav_sel"
            
        elif step == "goals_in":
            udetails[uid]["my_goals"] = txt_in
            await update.message.reply_text(
                "What type of content do you generally like?",
                reply_markup=get_see_menu()
            )
            context.user_data["cur_step"] = "see_sel"
            
        elif step == "place_in":
            udetails[uid]["my_place"] = txt_in
            acts = [
                [InlineKeyboardButton("All Done Profile", callback_data="finish_prof")],
                [InlineKeyboardButton("Go Back & Change", callback_data="fix_prof")]
            ]
            f_markup = InlineKeyboardMarkup(acts)
            await update.message.reply_text(
                "Profile made! Check info:\n"
                f"{show_prof_data(udetails[uid])}\n"
                "What's next?:",
                reply_markup=f_markup,
                parse_mode="Markdown"
            )
            
    elif "edit_fld" in context.user_data:
        f_name = context.user_data["edit_fld"]["fld"]
        
        if f_name == "age":
            try:
                n_age = int(txt_in)
                if not 10 <= n_age <= 120:
                    await update.message.reply_text("Age must be 10-120.")
                    return
                udetails[uid]["age"] = n_age
            except ValueError:
                await update.message.reply_text("Please use numbers for age.")
                return
        elif f_name == "about_me" and len(txt_in) > 500:
            await update.message.reply_text("Desc too long (max 500 chars).")
            return
        elif f_name == "see_type": 
            await update.message.reply_text("Please select a content type from the buttons provided.")
            await update.message.reply_text(
                "What type of content do you like to see?",
                reply_markup=get_see_menu(udetails[uid].get("see_type"))
            )
            return
        else:
            udetails[uid][f_name] = txt_in
            
        await update.message.reply_text(f"✅ {f_name.replace('_', ' ').title()} changed!")
        await show_prof_and_opts(update.message, uid)
        context.user_data.clear()

async def show_prof_and_opts(msg, uid):
    pdata = udetails[uid]
    stat = "🌟 Super Mode On" if pdata.get('super_mode') else "🔒 Super Mode Off"
    
    await msg.reply_text(
        f"{stat}\n{show_prof_data(pdata)}",
        parse_mode="Markdown"
    )
    
    kbs = [
        [InlineKeyboardButton("Fix Profile", callback_data="fix_prof")],
    ]
    rm = InlineKeyboardMarkup(kbs)
    await msg.reply_text("What to do now?", reply_markup=rm)

def get_edit_menu(current_p):
    flds_offer = [
        ("Name", "my_name"),
        ("Age", "age"),
        ("Type", "p_type"),
        ("About Me", "about_me"),
        ("Favs", "favs"),
        ("Goals", "my_goals"),
        ("Place", "my_place"),
        ("What content?", "see_type")
    ]
    kbs = []
    for txt, key in flds_offer:
        if key in current_p:
            kbs.append([InlineKeyboardButton(txt, callback_data=f"edit_{key}")])
    
    kbs.append([InlineKeyboardButton("Back to Profile", callback_data="see_prof")])
    return InlineKeyboardMarkup(kbs)

def get_type_menu(sel_it=None):
    cats = ["Dev", "Design", "Writer", "Student", "Other"]
    kbs = []
    for cat in cats:
        txt = f"✅ {cat}" if cat == sel_it else cat
        kbs.append([InlineKeyboardButton(txt, callback_data=f"type_{cat}")])
    return InlineKeyboardMarkup(kbs)

def get_fav_menu(curr_sel=None, is_create=False, is_edit=False):
    if curr_sel is None:
        curr_sel = []
    avail_favs = [
        "Code", "Art", "Read", "Sports",
        "Cook", "Music", "Games", "Pics"
    ]
    
    kbs = []
    for i in range(0, len(avail_favs), 2):
        rows = []
        for item in avail_favs[i:i+2]:
            txt = f"✅ {item}" if item in curr_sel else item
            rows.append(InlineKeyboardButton(txt, callback_data=f"fav_{item}"))
        kbs.append(rows)
    
    if is_create or is_edit:
        kbs.append([InlineKeyboardButton("✅ OK Favs", callback_data="ok_favs")])
    
    return InlineKeyboardMarkup(kbs)

def get_see_menu(sel_opt=None):
    prefs = ["Tech News", "Creative", "Learn", "Fun", "General"]
    kbs = []
    for opt in prefs:
        txt = f"✅ {opt}" if opt == sel_opt else opt
        kbs.append([InlineKeyboardButton(txt, callback_data=f"see_{opt}")])
    return InlineKeyboardMarkup(kbs)

def show_prof_data(pdict):
    return f"""
*Your Profile*
━━━━━━━━━━━━━━━━
*Name*: {pdict.get('my_name', 'No name')}
*Age*: {pdict.get('age', 'No age')}
*Type*: {pdict.get('p_type', 'No type')}
*Place*: {pdict.get('my_place', 'No place')}

*Favs*: {', '.join(pdict.get('favs', [])) if 'favs' in pdict else 'None'}
*About Me*: {pdict.get('about_me', 'No bio')}
*Goals*: {pdict.get('my_goals', 'No goals')}

*Content Type*: {pdict.get('see_type', 'No type')}
━━━━━━━━━━━━━━━━
"""

def make_bot():
    app = Application.builder().token(bot_key).build()
    
    app.add_handler(CommandHandler("start", go_start))
    app.add_handler(CommandHandler("profile", see_prof))
    
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_in))
    app.add_handler(CallbackQueryHandler(handle_button))

    logger.info("Bot is on...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    make_bot()
