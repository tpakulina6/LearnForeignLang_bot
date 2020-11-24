import datetime
from telegram.ext import Updater, CommandHandler, CallbackContext
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from environs import Env


langs = ['en', 'sp']
chatId_lang = {}
chatId_time = {}
en_dict = {
    'Hello': 'Привет',
    'I': 'Я',
    'Word': 'Слово',
    'Love': 'Любить'
}
sp_dict = {
    'Holla': 'Привет'
}
lang_dict = {'en': en_dict, 'sp': sp_dict}

en_list = []
for key in en_dict.keys():
    en_list.append('{} - {}'.format(key, en_dict[key]))


def start(update, context):
    update.message.reply_text(
        'Привет! Это телеграм бот для изучения иностранных слов. '
        'Выбери язык, который ты хочешь изучать и в течение дня тебе будут приходить 10 слов. '
        'Чтобы выбрать язык используй /set <language>, чтобы отписаться используй /unset. '
        'Ты можешь изучать любой из этих языков: {} '.format(', '.join(langs)))


def new_word(context):
    """Send new word."""
    job = context.job
    context.bot.send_message(job.context, text='{}'.format(en_list[0]))


def set_lang(update, context):
    chat_id = update.message.chat_id
    if chat_id not in chatId_lang:
        chatId_lang[chat_id] = []
        # chatId_time[chat_id] =
    try:
        # args[0] should contain the time for the timer in seconds
        lang = context.args[0]
        if lang not in langs:
            update.message.reply_text(
                'Извините, мы пока не можем помочь вам в изучении данного языка. '
                'Но мы это учтем и возможно скоро можно будет изучать этот язык у нас. ')
            return

        context.job_queue.run_daily(new_word, datetime.time(9, 43, 00, 000000), context=chat_id, name=str(chat_id))

        update.message.reply_text('Язык успешно выбран')

    except (IndexError, ValueError):
        update.message.reply_text('Используй /set <language>')


if __name__ == '__main__':
    env = Env()
    env.read_env()
    token = env.str('TOKEN')

    updater = Updater(token=token, use_context=True)
    dispatcher = updater.dispatcher

    start_handler = CommandHandler('start', start)
    dispatcher.add_handler(start_handler)

    start_handler = CommandHandler('help', start)
    dispatcher.add_handler(start_handler)

    start_handler = CommandHandler('set', set_lang, pass_job_queue=True)
    dispatcher.add_handler(start_handler)

    updater.start_polling()
    updater.idle()
