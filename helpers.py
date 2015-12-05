#!/usr/bin/python
# -*- coding: utf-8 -*-

def split_query_to_params(query, separator=u'\u25b6'):
    params = query.split(separator)
    return map(unicode.strip, params)

def yt_title(name):
    '''
    Splits yt_ names and titles them to present to user
    :param name:
    :return:
    '''
    return name.split('_')[1].title()