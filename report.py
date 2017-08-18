#!/usr/bin/python3

import argparse
import sys
import time
from datetime import datetime
import os
import requests
from jinja2 import Environment, FileSystemLoader, select_autoescape
from tzlocal import get_localzone
import operator

from __private import warcraftlogs_key

jenv = Environment(
    loader=FileSystemLoader('{}/templates'.format(os.path.dirname(__file__))),
    autoescape=select_autoescape(['html'])
)

local_tz = get_localzone()


player_classes = [
    'DeathKnight',
    'DemonHunter',
    'Druid',
    'Hunter',
    'Mage',
    'Monk',
    'Paladin',
    'Priest',
    'Rogue',
    'Shaman',
    'Warlock',
    'Warrior',
]


class Player:
    def __init__(self, guid, name, klass):
        self.guid = int(guid)
        self.name = name
        self.klass = klass
        self.present_reports = []
        self.late_reports = []
        self.early_leave_reports = []
        self.absent_reports = []
        self.present_days = [0] * 7
        self.late_days = [0] * 7
        self.early_leave_days = [0] * 7
        self.absent_days = [0] * 7
        self.total_days = [0] * 7

    def __eq__(self, other):
        return self.guid == other.guid

    def __hash__(self):
        return self.guid


def get_wcl_reports(guild, realm, region, start_time, end_time, zone_id):
    # get report ids
    start_str = datetime.utcfromtimestamp(start_time).strftime('%a %d/%m/%y %H:%S GMT')
    end_str = datetime.utcfromtimestamp(end_time).strftime('%a %d/%m/%y %H:%S GMT')
    print('Requesting WarcraftLogs data for reports between {} and {}'.format(start_str, end_str))
    resp = requests.get('https://www.warcraftlogs.com:443/v1/reports/guild/{}/{}/{}?start={}&end={}&api_key={}'.format(
        guild, realm, region, start_time * 1000, end_time * 1000, warcraftlogs_key))
    if resp.status_code != 200:
        print('Error: Failed to fetch report list from warcraftlogs. The guild, realm, or region is likely incorrect.')
        sys.exit(1)
    all_report_ids = resp.json()
    report_ids = []
    for r in all_report_ids:
        if r['zone'] == zone_id:
            report_ids.append(r)
    print('Success: Received {} report IDs'.format(len(report_ids)))

    # get fight data for each report
    reports = []
    for r in report_ids:
        resp = requests.get(
            'https://www.warcraftlogs.com:443/v1/report/fights/{}?api_key={}'.format(r['id'], warcraftlogs_key))
        if resp.status_code != 200:
            print('Error: Failed to a report from warcraftlogs. Ignoring it. (id={}, code={}, reason="{}")'.format(r['id'], resp.status_code, resp.reason))
            continue
        report = resp.json()
        report['id'] = r['id']
        reports.append(report)
        print('Success: Received fight data for report id={}'.format(report['id']))
    print('Success: Received fight data for {} report(s)'.format(len(reports)))
    return reports


def player_was_late(friendly):
    return len(friendly['fights']) > 0 and \
           friendly['fights'][0]['id'] != 1


def player_left_early(friendly, report):
    return len(friendly['fights']) > 0 and \
           len(report['fights']) > 0 and \
           friendly['fights'][-1]['id'] != report['fights'][-1]['id']


def get_players(report):
    players = []
    for friend in report['friendlies']:
        if friend['type'] in player_classes:
            players.append(friend)
    return players


def get_unique_players(reports):
    unique_players = set()
    for report in reports:
        for player in get_players(report):
            unique_players.add(Player(player['guid'], player['name'], player['type']))
    return list(unique_players)


def render_template(players):
    for player in players:
        player.attendance_rate = [-1] * 7
        for day in range(7):
            if player.total_days[day] == 0:
                player.attendance_rate[day] = 0
            else:
                player.attendance_rate[day] = round(player.present_days[day] / player.total_days[day] * 100)
    players.sort(key=operator.attrgetter('name'))
    template = jenv.get_template('week.html')
    with open('week.html', 'w') as f:
        f.write(template.render(players=players))
    print('Success: Rendered week attendance report')


def generate_attendance_report(reports):
    unique_players = get_unique_players(reports)
    for player in unique_players:
        for report in reports:
            player_in_report = False
            start_dt = datetime.fromtimestamp(int(report['start']) / 1000, local_tz)
            player.total_days[start_dt.weekday()] += 1
            for friend in report['friendlies']:
                if friend['guid'] == player.guid:
                    player_in_report = True
                    player.present_reports.append(report)
                    if player_was_late(friend):
                        player.late_reports.append(report)
                    if player_left_early(friend, report):
                        player.early_leave_reports.append(report)
            if not player_in_report:
                player.absent_reports.append(report)
        for report in player.present_reports:
            start_dt = datetime.fromtimestamp(int(report['start']) / 1000, local_tz)
            player.present_days[start_dt.weekday()] += 1
        for report in player.late_reports:
            start_dt = datetime.fromtimestamp(int(report['start']) / 1000, local_tz)
            player.late_days[start_dt.weekday()] += 1
        for report in player.early_leave_reports:
            start_dt = datetime.fromtimestamp(int(report['start']) / 1000, local_tz)
            player.early_leave_days[start_dt.weekday()] += 1
        for report in player.absent_reports:
            start_dt = datetime.fromtimestamp(int(report['start']) / 1000, local_tz)
            player.absent_days[start_dt.weekday()] += 1
    print('Success: Processed report data')
    return unique_players


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generates an attendance report from warcraft logs data')
    parser.add_argument('--start', '-s',
                        default=0,
                        type=int,
                        help='Unix time stamp (default=0)')
    parser.add_argument('--end', '-e',
                        default=-1,
                        type=int,
                        help='Unix time stamp (default=now)')
    parser.add_argument('--zone', '-z',
                        default='ToS',
                        type=str,
                        help='Possible values: EN, ToV, NH, ToS, ABT (default=latest)')
    parser.add_argument('--guild', '-g',
                        type=str,
                        default='riptide',
                        help='Guild name (default=riptide)')
    parser.add_argument('--realm', '-r',
                        type=str,
                        default='frostmourne',
                        help='Realm name as it appears in armoury URL (default=frostmourne)')
    parser.add_argument('--region', '-R',
                        type=str,
                        default='us',
                        help='Region code (default=us)')
    args = parser.parse_args()

    zones = {
        'EN': 10,
        'ToV': 12,
        'NH': 11,
        'ToS': 13,
        'ABT': 14,
    }

    zone_id = zones[args.zone]

    if args.end == -1:
        end_time = int(time.time())
    else:
        end_time = args.end

    wcl_reports = get_wcl_reports(args.guild, args.realm, args.region, args.start, end_time, zone_id)
    players = generate_attendance_report(wcl_reports)
    render_template(players)
