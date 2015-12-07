#!/usr/bin/python
# -*- coding: utf-8 -*-
import argparse
import sys
from functools import wraps

from helpers import split_query_to_params, yt_title
from workflow import Workflow, ICON_SETTINGS
from youtrack.connection import Connection

SEPARATOR = u'▶'

def add_yt_conneciton(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        wf = Workflow()
        yt_conn = Connection(wf.stored_data('yt_url'), wf.stored_data('yt_username'), wf.get_password(u'yt_password'))
        r = f(*args, yt_conn = yt_conn, **kwargs)
        return r
    return wrapped

def main(wf):
    query = wf.pargs.query # Ensure `query` is initialised
    filtered_project_names = []

    projects = wf.cached_data('projects', get_projects, max_age=60 * 60 * 24 * 100)

    ## Handle default project setting
    stored_default_project = projects.get(wf.stored_data('default_project'))
    if(stored_default_project and query is None):
        query = stored_default_project.strip()

    if query:
        filtered_project_names = wf.filter(query, projects.values(), min_score=20)

    # Show error if there are no results. Otherwise, Alfred will show
    # its fallback searches (i.e. "Search Google for 'XYZ'")
    if query and not filtered_project_names:
        wf.add_item('Could not find a project matching \'%s\'' % query, icon='')

    for id, project in projects.iteritems():
        if project in filtered_project_names or query is None:
            wf.add_item(project,
                        'Open a new issue in %s #%s. ' % (project, id),
                        arg= id + SEPARATOR,
                        valid=True,
                        icon='')
    wf.send_feedback()


@add_yt_conneciton
def get_issue_types(**kwargs):
    types = kwargs["yt_conn"].getEnumBundle('Types')
    return [x["name"] for x in types.values]

@add_yt_conneciton
def get_projects(**kwargs):
    return kwargs['yt_conn'].getProjects()

def filter_issue_types(wf):
    types = wf.cached_data('bundle_types', get_issue_types, max_age=3600)
    if wf.params[1] == '':
        wf.add_item('Choose type of issue (Default: Task)', subtitle='Default: Task, others can be Feature, Bug, Cosmetics...',
                    autocomplete=wf.params[0] + SEPARATOR + 'Task' + SEPARATOR,
                    icon='')
    else:
        issue_types = wf.filter(wf.params[1], types, min_score=20)
        for type in issue_types:
            wf.add_item(type,
                        'Open issue of type %s' % (type), icon='',
                        autocomplete=wf.params[0] + SEPARATOR + type + SEPARATOR
                        )
    wf.send_feedback()

def add_ticket_title(wf):
    log.error(wf.args)
    if wf.params[2] == '':
        wf.add_item('Enter issue title please', icon='')
    else:
        wf.add_item('Submit issue',
                    subtitle='"%s"' % wf.params[2],
                    arg=wf.args[1],
                    valid=True)
    wf.send_feedback()

def set_default_project(wf):
    project_id = split_query_to_params(wf.pargs.default_project)[0]
    wf.store_data('default_project',project_id)
    return wf.pargs.default_project

@add_yt_conneciton
def create_issue(wf, **kwargs):
    yt_conn = kwargs['yt_conn']
    project_id, project_type, project_summary = split_query_to_params(wf.pargs.issue)
    try:
        res = yt_conn.createIssue(project_id,None,project_summary, None,type=project_type)
        if res[0].get('location'):
            issue_id = res[0]['location'].split('/')[-1]
            url = wf.stored_data('yt_url') + '/issue/' + issue_id
            print url
    except Exception as e:
        print e.message
    sys.exit()

if __name__ == u"__main__":
    # Initiate the workflow object
    wf = Workflow()
    log = wf.logger
    log.error('Workflow ran with the following parameters : %s' % wf.args)

    #Parse some arguments so we better understand what the user is here to do
    parser = argparse.ArgumentParser()
    parser.add_argument('--default-project', dest='default_project', nargs='?', default=None)
    parser.add_argument('--create-issue', dest='issue', nargs='?', default=None)
    parser.add_argument('--open-issue', dest='open_issue', nargs='?', default=None)
    parser.add_argument('--set', dest='set', nargs='?', default=None)
    parser.add_argument('--reset', dest='reset', nargs='?', default=None)
    parser.add_argument('query', nargs='?', default=None)

    ## Save the parsed arguments in the wf object for later access
    wf.pargs = parser.parse_args(wf.args)

    #Check if the user wants to initiate settings saving
    if wf.pargs.reset:
        wf.delete_password(u'yt_password')
        wf.reset()
        sys.exit()

    if wf.pargs.set:
        params = split_query_to_params(wf.pargs.set)
        if len(params) == 3:
            # if we have 3 params, means the user already chose a setting and filled it
            log.error('User wants to save something!! %s' % wf.pargs)
            if params[0] == 'yt_password':
                wf.save_password(u'yt_password', params[1])
            else:
                wf.store_data(params[0], params[1])
            print "Saved %s sucesfully!" % yt_title(params[0])
            sys.exit()
        if params[1] == '':
            wf.add_item('Please enter your YouTrack %s' % yt_title(params[0]),subtitle=u'Cannot be empty!', icon=ICON_SETTINGS)
        else:
            wf.add_item('Set your YouTrack %s to \'%s\'' % (yt_title(params[0]),params[1]),
                        subtitle=u'Hit enter to set.',
                        icon=ICON_SETTINGS,
                        arg=wf.pargs.set + SEPARATOR,
                        valid=True)
        wf.send_feedback()

    settings = {}
    settings['yt_url'] = wf.stored_data('yt_url')
    settings['yt_username'] = wf.stored_data('yt_username')
    try:
        settings['yt_password'] = wf.get_password(u'yt_password')
    except:
        settings['yt_password'] = None
    missing_settings = {key: value for (key, value) in settings.iteritems() if not value}
    if len(missing_settings.keys()):
        for k in missing_settings:
            wf.add_item(u'Youtrack %s not set.' % yt_title(k),
                        subtitle='Set your Youtrack %s' % yt_title(k),
                        modifier_subtitles={'cmd':'Please don\' press cmd on the settings option, there be dragons'},
                        arg='%s' % k.lower(),
                        valid=True,
                        icon=ICON_SETTINGS)
        wf.send_feedback()
        sys.exit()

    if wf.pargs.issue:
        ## Create issue with --create-issue
        log.error('Create issue was ran with the following parameters: %s' % wf.args)
        res = wf.run(create_issue)
    elif wf.pargs.default_project:
        ## Set default project with --default-project
        res = wf.run(set_default_project)
    elif wf.pargs.open_issue:
        wf.params = split_query_to_params(wf.pargs.open_issue)
        log.error(wf.pargs)
        if len(wf.params) == 2:
            res = wf.run(filter_issue_types)
        elif len(wf.params) == 3:
            res = wf.run(add_ticket_title)
        else:
            wf.add_item(u'Please type YT to run the workflow again.', subtitle=u'Or ask alex why he can\'t make it work like this')
            wf.send_feedback()
    else:
        ## u'\u25b6' represents the ▶︎︎ character which I use to split params in alfred.
        ## if there's more then 1 item after the split it means there are several params
        if wf.pargs.query:
            wf.params = split_query_to_params(wf.pargs.query)
        else:
            wf.params = ()
        res = wf.run(main)
    sys.exit(res)
