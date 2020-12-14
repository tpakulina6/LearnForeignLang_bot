import datetime
import logging
import random
import sqlite3
from environs import Env
from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext
from deep_translator import GoogleTranslator
import pandas as pd


logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

lang_dict = {'en': 'en_words.csv', 'es': 'es_words.csv'}
langs = ['en', 'es']


def create_table():
    connection = sqlite3.connect('telebot.db')
    connection_cursor = connection.cursor()
    connection_cursor.execute('''Drop TABLE IF EXISTS new_words''')
    connection_cursor.execute('''CREATE TABLE new_words
                     (date text, chat_id INTEGER, lang text, word_id INTEGER, status text)''')
    connection.commit()
    connection.close()


def time_start_end(diff_time):
    new_start_hour = (diff_time // 60 + 11) % 24
    new_end_hour = (diff_time // 60 + 20) % 24
    new_minute = diff_time % 60
    return new_start_hour, new_end_hour, new_minute


def print_new_time(diff_time):
    new_start_hour, new_end_hour, new_minute = time_start_end(diff_time)
    if new_minute < 10:
        new_minute_text = f'0{new_minute}'
    else:
        new_minute_text = str(new_minute)
    string_with_time = f'Новые слова будут появляться каждый час с {new_start_hour}.{new_minute_text} ' \
                       f'до {new_end_hour}.{new_minute_text} по московскому времени.'
    return string_with_time


def time_interval_sent_new_word(new_start_h, new_end_h):
    if new_end_h < 9:
        time_interval_after_midnight = list(range(new_end_h + 1))
        time_interval_before_midnight = list(range(new_start_h, 24))
        time_interval = time_interval_before_midnight + time_interval_after_midnight
    else:
        time_interval = list(range(new_start_h, new_end_h + 1))
    return time_interval


def change_status_word(chat_id, lang, word_id, status):
    conn = sqlite3.connect('telebot.db')
    conn_cursor = conn.cursor()
    conn_cursor.execute(f"UPDATE new_words SET status = '{status}' where chat_id = {chat_id} "
                        f"and lang = '{lang}' and word_id = {word_id} ")
    conn.commit()
    conn.close()


def insert_new_word(chat_id, lang, index):
    conn = sqlite3.connect('telebot.db')
    conn_cursor = conn.cursor()
    conn_cursor.execute((f"INSERT INTO new_words "
                         f"VALUES ('{datetime.datetime.today().strftime('%Y-%m-%d')}',"
                         f"'{chat_id}','{lang}', '{index}','{'new'}')"))
    conn.commit()
    conn.close()


def indexes_learn(chat_id, lang):
    conn = sqlite3.connect('telebot.db')
    conn_cursor = conn.cursor()
    indexes = [id[0] for id in
               list(conn_cursor.execute(f"SELECT word_id FROM new_words "
                                        f"where chat_id = {chat_id} and lang = '{lang}' "))]
    conn.close()
    return indexes


def not_known_words_id(chat_id, lang):
    conn = sqlite3.connect('telebot.db')
    conn_cursor = conn.cursor()
    words_id = [id[0] for id in list(conn_cursor.execute(
        f"SELECT word_id FROM new_words where chat_id = {chat_id} "
        f"and lang = '{lang}' and status != 'known' "))]
    conn.close()
    return words_id


def status_word(chat_id, lang, word_id):
    conn = sqlite3.connect('telebot.db')
    conn_cursor = conn.cursor()
    status = [id[0] for id in list(conn_cursor.execute(
        f"SELECT status FROM new_words where chat_id = {chat_id} "
        f"and lang = '{lang}' and word_id = {word_id} and status != 'known' "))]
    conn.close()
    return status


def start(update: Update, context: CallbackContext):
    update.message.reply_text(
        'Привет! Это телеграм бот для изучения иностранных слов. '
        'Выбери язык, который ты хочешь изучать и в течение дня тебе будут приходить 10 слов. '
        'Чтобы выбрать язык используй /set <language>, чтобы отписаться используй /unset <language>. '
        'Ты можешь изучать любой из этих языков: {} '.format(', '.join(langs)))
    update.message.reply_text(
        'В любой момент вы можете проверить, как хорошо вы выучили слова, которые вам прислали.'
        'Для этого используйте /test_words <lang> <количество слов, которое вы хотите проверить>')


def new_word(context: CallbackContext):
    """Send new word."""
    chat_id = context.job.context
    languages = context.dispatcher.chat_data[chat_id]['lang']
    for lang in languages:
        df_all_words = pd.read_csv(lang_dict[lang])
        indexes = indexes_learn(chat_id, lang)
        df_words = df_all_words.loc[~df_all_words.index.isin(indexes)]
        if len(df_words) == 0:
            context.bot.send_message(chat_id, text='Слова закончились, но скоро мы добавим новые. '
                                                   'Может вы хотите изучать еще какой-то язык?')
            return
        index = random.choice(df_words.index)
        word = df_words.iloc[index, 0]
        ru_word = GoogleTranslator(source='auto', target='ru').translate(word)
        context.bot.send_message(chat_id, text=f'#{index} {lang}: {word} - {ru_word}')
        insert_new_word(chat_id, lang, index)


def set_lang(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    try:
        lang = context.args[0]
        if lang not in langs:
            update.message.reply_text(
                'Извините, мы пока не можем помочь вам в изучении данного языка. '
                'Но мы это учтем и возможно скоро можно будет изучать этот язык у нас. ')
            return
        current_jobs = context.job_queue.get_jobs_by_name(str(chat_id))
        if not current_jobs:
            context.chat_data.update({'lang': [lang]})

            for hour in range(11, 21):
                context.job_queue.run_daily(new_word, datetime.time(hour, 0), context=chat_id, name=str(chat_id))
            update.message.reply_text(
                'Отличный выбор! Новые слова будут появляться каждый час с 11.00 до 20.00 по московскому времени. '
                'Если вы хотите изменить время, то использойте /change_time <minutes(best_time_for_you - Moscow_time)>'
            )
        else:
            if lang in context.chat_data['lang']:
                update.message.reply_text('Вы уже изучаете этот язык. Скоро вам придет новое слово.')
            else:
                context.chat_data['lang'].append(lang)

                if 'time_diff' not in context.chat_data.keys():
                    diff_time = 0
                else:
                    diff_time = context.chat_data['time_diff']

                string_with_time = print_new_time(diff_time)

                update.message.reply_text(
                    'Отлично, вы теперь изучаете несколько языков!' + string_with_time + ' Если вы хотите '
                    'изменить время, то использойте /change_time <minutes(best_time_for_you - Moscow_time)>'
                )
        update.message.reply_text('Если вы знаете слово, то вы можете пометить его, '
                                  'как знакомое командой /know_word <lang> <word_id>, '
                                  'иначе мы запишем его к незнакомым словам.')

    except (IndexError, ValueError):
        update.message.reply_text('Используй /set <language>')


def unset_lang(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    try:
        lang = context.args[0]
        if 'lang' not in context.chat_data.keys() or lang not in context.chat_data['lang']:
            update.message.reply_text('Вы не выбирали этот язык')
            return

        del context.chat_data['lang'][context.chat_data['lang'].index(lang)]
        if len(context.chat_data['lang']) > 0:
            if 'time_diff' not in context.chat_data.keys():
                diff_time = 0
            else:
                diff_time = context.chat_data['time_diff']

            string_with_time = print_new_time(diff_time)
            update.message.reply_text(
                    'Очень жаль, что вы не хотите изучать этот язык. '
                    'Но у вас есть еще что изучать. ' + string_with_time + ' Если вы '
                    'хотите изменить время, то использойте '
                    '/change_time <minutes(best_time_for_you - Moscow_time)>'
                )
        else:
            current_jobs = context.job_queue.get_jobs_by_name(str(chat_id))
            for job in current_jobs:
                job.schedule_removal()
            context.chat_data.update({'time_diff': 0})
            update.message.reply_text(
                'Вы больше не изучаете этот язык. Может вы хотите попоробовать другой язык? '
                'Мы можем вам предложить еще изучение этих языков: {} '.format(
                    ', '.join([lan for lan in langs if lan != lang]))
            )

    except (IndexError, ValueError):
        update.message.reply_text('Используй /unset <language>')


def change_time(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    try:
        if 'lang' not in context.chat_data.keys() or len(context.chat_data['lang']) == 0:
            update.message.reply_text('Вы еще не начинали изучать новые слова. '
                                      'Чтобы начать их изучать напишите /set <language>')
            return
        diff_time = int(context.args[0])
        if diff_time == 0 or (
                'time_diff' in context.chat_data.keys() and context.chat_data['time_diff'] == diff_time):
            update.message.reply_text('Зачем менять шило на мыло? У вас и так было выбрано это время.')
            return

        context.chat_data.update({'time_diff': diff_time})

        current_jobs = context.job_queue.get_jobs_by_name(str(chat_id))
        for job in current_jobs:
            job.schedule_removal()

        new_start_hour, new_end_hour, new_minute = time_start_end(diff_time)
        string_with_time = print_new_time(diff_time)
        time_interval = time_interval_sent_new_word(new_start_hour, new_end_hour)
        for hour in time_interval:
            context.job_queue.run_daily(new_word, datetime.time((hour - 3) % 24, new_minute), context=chat_id,
                                        name=str(chat_id))
        update.message.reply_text('Время отправки сообщений изменено. ' + string_with_time)

    except (IndexError, ValueError):
        update.message.reply_text('Используй /change_time <minutes(best_time_for_you - Moscow_time)>')


def know_word(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    try:
        lang = context.args[0]
        word_id = int(context.args[1])

        words_status = status_word(chat_id, lang, word_id)
        if len(words_status) == 0 or words_status[0] != 'new':
            update.message.reply_text(
                'Этого слова нет в новых словах. Попробуйте еще раз.')
            return

        change_status_word(chat_id, lang, word_id, 'good_word')
        update.message.reply_text(
            'Статус слова успешно изменен')

    except (IndexError, ValueError):
        update.message.reply_text('Используйте /know_word <lang> <word_id>')


def test_words(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    try:
        lang = context.args[0]
        cnt = int(context.args[1])

        if lang not in langs:
            update.message.reply_text(
                'Такого языка нет. Но мы учтем ваши пожелания.')
            return
        if cnt <= 0:
            update.message.reply_text(
                'Введите число больше 0')
            return

        words_id = not_known_words_id(chat_id, lang)

        if len(words_id) == 0:
            update.message.reply_text(
                'Все новые слова выучены.')
            return

        df_all_words = pd.read_csv(lang_dict[lang])

        update.message.reply_text(f'Переведите слова на {lang} с помощю команды и напишите ответ в виде'
                                  f' /translate {lang} <word_id> <ВАШ ПЕПЕВОД>')
        for index in random.sample(words_id, min(cnt, len(words_id))):
            word = str(df_all_words.iloc[index, 0])
            update.message.reply_text(f"#{index} на {lang}: "
                                      f"{GoogleTranslator(source='auto', target='ru').translate(word)}")

    except (IndexError, ValueError):
        update.message.reply_text('Используйте /test_words <lang> <количество слов, которое вы хотите проверить>')


def translate_word(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    try:
        lang = context.args[0]
        word_id = int(context.args[1])
        word = context.args[2]

        status = status_word(chat_id, lang, word_id)
        if len(status) == 0:
            update.message.reply_text(
                'Этого слова нет в неизученных словах. Попробуйте еще раз.')
            return

        df_all_words = pd.read_csv(lang_dict[lang])
        true_word = df_all_words.iloc[word_id, 0]
        if word == true_word:
            if status[0] == 'new':
                change_status_word(chat_id, lang, word_id, 'good_word')
                update.message.reply_text(
                    'Отлично! Вы ответили правильно! Статус слова изменен.')
            elif status[0] == 'good_word':
                change_status_word(chat_id, lang, word_id, 'known')
                update.message.reply_text(
                    'Отлично! Вы ответили правильно! Слово добавлено в изученные слова.')
        else:
            if status[0] == 'good_word':
                change_status_word(chat_id, lang, word_id, 'new')

            update.message.reply_text(
                f'Это неправильный перевод. Правильный перевод: {true_word}')

    except (IndexError, ValueError):
        update.message.reply_text('Используйте /translate <lang> <word_id> <ВАШ ПЕПЕВОД>')


if __name__ == '__main__':
    create_table()
    env = Env()
    env.read_env()
    token = env.str('TOKEN')

    updater = Updater(token=token, use_context=True)
    dispatcher = updater.dispatcher

    start_handler = CommandHandler('start', start)
    dispatcher.add_handler(start_handler)

    start_handler = CommandHandler('help', start)
    dispatcher.add_handler(start_handler)

    set_handler = CommandHandler('set', set_lang)
    dispatcher.add_handler(set_handler)

    unset_handler = CommandHandler('unset', unset_lang)
    dispatcher.add_handler(unset_handler)

    change_time_handler = CommandHandler('change_time', change_time)
    dispatcher.add_handler(change_time_handler)

    know_word_handler = CommandHandler('know_word', know_word)
    dispatcher.add_handler(know_word_handler)

    test_words_handler = CommandHandler('test_words', test_words)
    dispatcher.add_handler(test_words_handler)

    translate_handler = CommandHandler('translate', translate_word)
    dispatcher.add_handler(translate_handler)

    updater.start_polling()
    updater.idle()
