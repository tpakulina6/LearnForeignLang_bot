import sqlite3
import pytest
from bot import (
    time_start_end,
    print_new_time,
    time_interval_sent_new_word,
    create_table,
    insert_new_word,
    change_status_word,
    indexes_learn,
    not_known_words_id,
    status_word,
)


def check_status(chat_id, lang, index):
    conn = sqlite3.connect('telebot.db')
    conn_cursor = conn.cursor()
    new_word_status = [id[0] for id in
                       list(conn_cursor.execute(f"SELECT status FROM new_words "
                                                f"where chat_id = {chat_id} and lang = '{lang}'"
                                                f" and word_id = {index} "))]
    conn.close()
    return new_word_status


time_start_end_examples = [
    (2, 11, 20, 2),
    (62, 12, 21, 2),
    (242, 15, 0, 2),
]


@pytest.mark.parametrize('diff_time, expected_start_hour, expected_end_hour, expected_minute', time_start_end_examples)
def test_time_start_end(diff_time, expected_start_hour, expected_end_hour, expected_minute):
    print('test_time_start_end')
    new_start_hour, new_end_hour, new_minute = time_start_end(diff_time)
    assert new_start_hour == expected_start_hour
    assert new_end_hour == expected_end_hour
    assert new_minute == expected_minute


print_new_time_examples = [
    (2, 11, 20, '02'),
    (62, 12, 21, '02'),
    (242, 15, 0, '02'),
    (240, 15, 0, '00'),
    (250, 15, 0, '10'),
    (30, 11, 20, '30'),
]


@pytest.mark.parametrize('diff_time, new_start_hour, new_end_hour, new_minute_text', print_new_time_examples)
def test_print_new_time(diff_time, new_start_hour, new_end_hour, new_minute_text):
    print('test_print_new_time')
    string_with_time = print_new_time(diff_time)
    assert string_with_time == f'Новые слова будут появляться каждый час с {new_start_hour}.{new_minute_text} ' \
                               f'до {new_end_hour}.{new_minute_text} по московскому времени.'


time_interval_sent_new_word_examples = [
    (2, 11, [2, 3, 4, 5, 6, 7, 8, 9, 10, 11]),
    (19, 4, [19, 20, 21, 22, 23, 0, 1, 2, 3, 4]),
    (15, 0, [15, 16, 17, 18, 19, 20, 21, 22, 23, 0]),
    (0, 9, [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]),
]


@pytest.mark.parametrize('new_start_h, new_end_h, expected_time_interval', time_interval_sent_new_word_examples)
def test_time_interval_sent_new_word(new_start_h, new_end_h, expected_time_interval):
    print('test_time_interval_sent_new_word')
    time_interval = time_interval_sent_new_word(new_start_h, new_end_h)
    assert time_interval == expected_time_interval


create_table_examples = [()]


@pytest.mark.parametrize('', create_table_examples)
def test_create_table():
    print('test_create_table')
    connection = sqlite3.connect('telebot.db')
    connection_cursor = connection.cursor()
    connection_cursor.execute('''Drop TABLE IF EXISTS new_words''')
    connection.commit()
    connection.close()

    connection = sqlite3.connect('telebot.db')
    connection_cursor = connection.cursor()
    not_exist_table = len(
        list(connection_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='new_words' ")))
    connection.close()
    assert not_exist_table == 0

    create_table()
    connection = sqlite3.connect('telebot.db')
    connection_cursor = connection.cursor()
    exist_table = len(
        list(connection_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='new_words' ")))
    connection.close()
    assert exist_table == 1


insert_new_word_examples = [
    (1, 'en', 1),
    (111, 'es', 22),
]


@pytest.mark.parametrize('chat_id, lang, index', insert_new_word_examples)
def test_insert_new_word(chat_id, lang, index):
    print('test_insert_new_word')
    create_table()
    insert_new_word(chat_id, lang, index)
    new_word_status = check_status(chat_id, lang, index)
    assert len(new_word_status) == 1
    assert new_word_status[0] == 'new'


change_status_word_examples = [
    (1, 'en', 1, 'new'),
    (111, 'es', 22, 'good_word'),
    (999, 'es', 666, 'known'),
]


@pytest.mark.parametrize('chat_id, lang, index, status', change_status_word_examples)
def test_change_status_word(chat_id, lang, index, status):
    print('test_change_status_word')
    create_table()
    insert_new_word(chat_id, lang, index)
    change_status_word(chat_id, lang, index, status)
    new_word_status = check_status(chat_id, lang, index)
    assert len(new_word_status) == 1
    assert new_word_status[0] == status


indexes_learn_examples = [
    (1, 'en', [1, 2, 3], [4, 5, 6], [7, 8, 9], [1, 2, 3, 4, 5, 6, 7, 8, 9]),
    (1, 'en', [1, 2, 3], [], [7, 8, 9], [1, 2, 3, 7, 8, 9]),
    (1, 'en', [], [], [7, 8, 9], [7, 8, 9]),
    (1, 'en', [1, 2, 3], [4, 5, 6], [], [1, 2, 3, 4, 5, 6]),
]


@pytest.mark.parametrize('chat_id, lang, indexes_new, indexes_gw, indexes_kn, expected_indexes', indexes_learn_examples)
def test_indexes_learn(chat_id, lang, indexes_new, indexes_gw, indexes_kn, expected_indexes):
    print('test_change_status_word')
    create_table()
    for index in indexes_new + indexes_gw + indexes_kn:
        insert_new_word(chat_id, lang, index)
    for index in indexes_gw:
        change_status_word(chat_id, lang, index, 'good_word')
    for index in indexes_kn:
        change_status_word(chat_id, lang, index, 'known')
    indexes = indexes_learn(chat_id, lang)
    assert indexes == expected_indexes


not_known_words_examples = [
    (1, 'en', [1, 2, 3], [4, 5, 6], [7, 8, 9], [1, 2, 3, 4, 5, 6]),
    (1, 'en', [1, 2, 3], [], [7, 8, 9], [1, 2, 3]),
    (1, 'en', [], [], [7, 8, 9], []),
    (1, 'en', [1, 2, 3], [4, 5, 6], [], [1, 2, 3, 4, 5, 6]),
]


@pytest.mark.parametrize('chat_id, lang, indexes_new, indexes_gw, indexes_kn, exp_indexes', not_known_words_examples)
def test_not_known_words_id(chat_id, lang, indexes_new, indexes_gw, indexes_kn, exp_indexes):
    create_table()
    for index in indexes_new + indexes_gw + indexes_kn:
        insert_new_word(chat_id, lang, index)
    for index in indexes_gw:
        change_status_word(chat_id, lang, index, 'good_word')
    for index in indexes_kn:
        change_status_word(chat_id, lang, index, 'known')
    indexes = not_known_words_id(chat_id, lang)
    assert indexes == exp_indexes


status_word_examples = [
    (1, 'en', 1, 'new', ['new']),
    (1, 'en', 1, 'good_word', ['good_word']),
    (1, 'en', 1, 'known', []),
]


@pytest.mark.parametrize('chat_id, lang, word_id, status, expected_status', status_word_examples)
def test_status_word(chat_id, lang, word_id, status, expected_status):
    create_table()
    insert_new_word(chat_id, lang, word_id)
    change_status_word(chat_id, lang, word_id, status)
    status = status_word(chat_id, lang, word_id)
    assert status == expected_status
