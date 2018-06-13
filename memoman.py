#!/bin/python3

# -*- coding: utf-8 -*-
#==============================
#    Author: Elun Dai
#    Last modified: 2018-06-13 14:48
#    Filename: memoman.py
#    Description:
#    
#=============================#
import pandas as pd
import numpy as np
import os
from settings import *
from memory import S
import time, datetime
import re

class Memoman:
    def __init__(self):
        # load vocabulary
        df = pd.read_csv('3000.csv')
        df.index = df.word
        self.df = df

        # pickle
        if os.path.exists(USER_PICKLE):
            df_ulist = pd.read_pickle(USER_PICKLE)
        else:
            df_ulist = pd.DataFrame(columns=['word', 'count', 'corrects', 'grades', 'reviews', 'intervels', 'stabilities', 'times'])
            df_ulist.index = df_ulist.word

        self.df_ulist = df_ulist

        # user mongo database
#         client = pymongo.MongoClient(host='127.0.0.1',port=27017)
#         db = client.memoman
#         db_ulist = db.ulist
#         df_ulist = pd.DataFrame(list(db_ulist.find({}, projection={"_id": False})))
#         self.client = client
#         self.db = db
#         self.db_ulist = db_ulist
#         self.df_ulist = df_ulist

        # category
#         self.unstudied = df.drop(df_ulist.index)

    def _list_append(self, cell, item):
        """insert item to list cell
        """
        if isinstance(cell, np.ndarray):
            return np.append([cell, item])
        elif isinstance(cell, list):
            cell.append(item)
            return cell
        elif pd.isna(cell):
            return [item]
        else:
            raise ValueError('cell is not a list or ndarray or nan')
#             return [cell, item]


    def update(self, word_dicts):
        # if .loc 
        # new = self.df_ulist.loc[[d.get('word') for d in word_dicts]]
        new = self.df_ulist.reindex([d.get('word') for d in word_dicts])
        new.word = new.index
        new.loc[:, 'count'][pd.isna(new.loc[:, 'count'])] = 0
#         new.loc[:, 'stabilities'][pd.isna(new.loc[:, 'stabilities'])] = STABILITY

        for word_dict in word_dicts:
            label = word_dict.get('word')

            new.at[label, 'count'] += 1

            # append
            new.at[label, 'corrects'] = self._list_append(new.loc[label, 'corrects'], word_dict.get('correct'))
            new.at[label, 'times'] = self._list_append(new.loc[label, 'times'], word_dict.get('time'))
            new.at[label, 'grades'] = self._list_append(new.loc[label, 'grades'], np.mean(new.loc[label, 'corrects']))

            # compute intervel
            new.at[label, 'reviews'] = self._list_append(new.loc[label, 'reviews'], word_dict.get('review'))
            intervel = (word_dict.get('review') - new.loc[label, 'reviews'][-1]).total_seconds() / 60
            new.at[label, 'intervels'] = self._list_append(new.loc[label, 'intervels'], intervel)

            # compute stability
            if isinstance(new.loc[label, 'stabilities'], list):
                last_s = new.loc[label, 'stabilities'][-1]
            else:
                last_s = STABILITY
            stability = S(last_s, intervel, new.loc[label, 'corrects'][-1], new.loc[label, 'count'])
#                           a=LEARNINGRATE)
            new.at[label, 'stabilities'] = self._list_append(new.loc[label, 'stabilities'], stability)

            # update df_ulist
            self.df_ulist.loc[label] = new.loc[label]

        # update df_ulist
#         self.df_ulist.reindex(new.index).update(new)
        return new

    def compute_score(self, word):
        """return the score of a word in df_ulist"""
        now = datetime.datetime.fromtimestamp(time.time())
        intervel = (word.reviews[-1] - now).total_seconds() / 60
        # the higher score the more probability to be select
        score = sum([word['count'] < 10, # less re-encount times
            word['grades'][-1] < 0.5, # get wrong frequently
            intervel > 2 * word['stabilities'][-1], # shortern memory
            3 * (intervel > 20 * word['stabilities'][-1]), # longtern get 3 point
            (3 * STABILITY) / word['stabilities'][-1], # stability
            np.mean(word.times) > 3, # average answer time
            ]) + np.random.randint(0, 4) # add 1 or 2 or 3 randomly
        return score

    def get_list(self, total, from_studying=0, contain=None, wipe_out=None):
        """get list from df_ulist and df
        arguement:
            total: total number of words in the word list returned
            from_studying: value in [0, 1], the proposion of word studying contained in the list
            contain: a list or Series, composory contain in the word list.
            wipe_out: a list or Series, composory wipe out words from the word list
        """
        if from_studying < 0 or from_studying > 1:
            raise ValueError('from_studying should between 0 and 1')

        words = pd.DataFrame(columns=self.df.columns)
        df = self.df

        score = self.df_ulist.apply(memoman.compute_score, axis=1)
        if len(score) > 0:
            score.sort_values(ascending=False, inplace=True)

        if contain is not None:
            try:
                score = score.drop(contain)
            except ValueError:
                pass
#             df.drop(contain)
            words = words.append(df.loc[contain])

        if wipe_out is not None:
            try:
                score = score.drop(wipe_out)
            except ValueError:
                pass
            df = df.drop(wipe_out)

        if from_studying > 0:
            # BUG: when df is empty or none of score in df
            words = words.append(df.loc[score.index[:int((total - len(words)) * from_studying)]])
            # BUG: df contain duplicate columns
#             words = words.append(df.reindex(index=score.index[:int((total - len(words)) * from_studying)]))

        # from df - words
        words = words.append(df.drop(words.index).sample(total - len(words)))
        
        return words.sample(len(words)) # return shuffled words
    
    def study(self, n=7):
        repeat_last = False
        while True:
            if repeat_last is False:
                words = self.get_list(N_PER_LIST, from_studying=REVIEW_PROPOTION)
            else:
                repeat_last = False

            pass_test = False
            while pass_test is False:
                self.show_words(words)
                pass_test = self.test_memo(words)

            word_dicts = self.question(words)
#             if not isinstance(word_dicts, dict):
#                 return word_dicts

            # remove words in list from unstudied
#             self.unstudied.drop(words.index)

            # update df_ulist
            self.update(word_dicts)

#             print('user database updated!')

            # save
            self.df_ulist.to_pickle(USER_PICKLE)

            # review
            os.system('clear')
            print('review:')
            self.review_list(words)
            input('Press enter ...')

            # check pass
            os.system('clear')
            grade = np.sum([word_dict.get('correct') for word_dict in word_dicts]) / len(word_dicts)
            if grade < 0.8:
                print('Ops! you faild the test, only got {}'.format(grade))
                print('Please study this word list again!')
                input('Press enter ...')
                repeat_last = True
            else:
                # to next list
                ret = input('continue studying next list? (enter "q" to quit; enter "a" to study again): ')
                if ret.lower() in ['n', 'q', 'N', 'quit', 'no']:
                    break
                if ret.lower() in ['a', 'again']:
                    repeat_last = True
                    continue

    def review_list(self, words):
        words = words.copy()
        words.english = words.english.apply(lambda s: re.sub(r'(^|\n) *', r'\1\t', s))
        words.chinese = words.chinese.apply(lambda s: re.sub(r'(^|\n) *', r'\1\t', s))
        for idx in range(len(words)):
            print('({}) {}'.format(idx+1, words.word[idx]))
            print(words.chinese[idx])
            print(words.english[idx])
            print('')

    def show_words(self, words):
        n = len(words)
        for idx in range(n):
            word = words.iloc[idx]

            os.system('clear')
            print('word {}/{}'.format(idx+1, n))
            print('')
            print(word.chinese)
            print(word.english)
            input()

            print('----------')
            print(word.word)
            input()
            os.system('clear')

    def test_memo(self, words):
        correct = []
        pass_test = False
        N_COLUMN = 5
        format_str = '{:18}' * N_COLUMN
        for round_n in range(N_TEST_MEMO):
            # if n_in_words get 1, expand the number of words to [1, 2, 3]
            # i.e. 50% get 0, and 1, 2, 3 share the rest
            n_in_words = np.random.randint(0, 2) * np.random.randint(1, 4)
            contain = words.word.sample(n_in_words)
            choises = self.get_list(20, from_studying=0.5, contain=contain, wipe_out=words.word.drop(contain))
            choises_l = choises.word.as_matrix().reshape(-1, N_COLUMN)
            # print choises
            os.system('clear')
            print('test memory {}/{}'.format(round_n+1, N_TEST_MEMO))
            print()
            for row in choises_l:
                print(format_str.format(*row))

            print()
            ret = input('what is the number of words you studied just now? (If none of them, press enter).\n\tyour answer: ')
            if ret is '':
                ret = 0
            if int(ret) is n_in_words:
                correct.append(True)
            else:
                correct.append(False)

            if len(contain) > 0:
                print()
                print('words in this list:')
                print(', '.join(contain))
                print()
                input('Press enter ...')
            elif int(ret) is not 0:
                print('Wrong! None of them contained in the list.')
                input('')


        grade = np.sum(correct) / len(correct)
        if grade > 0.8:
            pass_test = True

        return pass_test

    def question(self, words):
#         try:
#             studied = self.df_ulist.drop(words.index)
#         except ValueError as e:
#             studied = self.df_ulist

        words = words.sample(len(words)) # shuffle
        word_dicts = []
        n = len(words)
        # for each word in word list
        for idx in range(n):
            word = words.iloc[idx]
            others = words.drop(word.word)
            start = time.time()

            # generate choises
            contain = [word.word]
            contain.extend(others.sample(2).word.as_matrix().tolist())
            choises = self.get_list(N_QUESTION, from_studying=0.5, contain=contain)
            # format string
            choises.english = choises.english.apply(lambda s: re.sub(r'(^|\n) *', r'\1\t', s))
            choises.chinese = choises.chinese.apply(lambda s: re.sub(r'(^|\n) *', r'\1\t', s))

            # print choises
            os.system('clear')
            print('question {}/{}'.format(idx+1, n))
            print()
            print(word.word)
            print('-'*20)
            print()
            round_n = 0
            correct = False
            for choise_id, choise in enumerate(choises.word):
                print('({}) '.format(choise_id % CHOISE_EACH_TIME +1))
                print(choises.loc[choise].chinese)
#                 if not isinstance(choises.loc[choise].chinese, str):
#                     return choises
                print()
                if (choise_id is not 0 and (choise_id + 1) % CHOISE_EACH_TIME is 0) or choise_id is len(choises) - 1:
                    res = input("choose your answer:  ")
                    # check answer
                    if res is not '':
                        correct = choises.iloc[round_n*CHOISE_EACH_TIME + int(res) -1].word == word.word
                        break

                    # print header again
                    os.system('clear')
                    print('question {}/{}'.format(idx+1, n))
                    print()
                    print(word.word)
                    print('-'*20)
                    print()
                    round_n += 1

            end = time.time()
            if correct is not True:
                os.system('clear')
                print('Sorry, you choose a wrong answer!\n'*20)
                input('Press enter ...')


            word_dict = {'word': word.word, 
                         'correct': correct,
                         'review': datetime.datetime.fromtimestamp(end),
                         'time':end - start,
                        }
            word_dicts.append(word_dict)
        return word_dicts

if __name__ == "__main__":
    memoman = Memoman()
#     memoman.study()
